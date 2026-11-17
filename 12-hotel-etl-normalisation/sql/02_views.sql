-- ============================================================================
-- Analysis views over the normalised booking schema.
--
-- Each of these needed a join across the lookup dimensions, which is the point
-- of normalising: the category names live in exactly one place.
-- ============================================================================

-- Flat view reconstructing the original wide table, for anyone who wants it
-- back. Useful as a sanity check that normalising lost nothing.
CREATE OR REPLACE VIEW v_booking_flat AS
SELECT b.booking_id,
       b.guest_id,
       b.reservation_date,
       b.adults,
       b.children,
       b.weekend_nights,
       b.week_nights,
       b.weekend_nights + b.week_nights          AS total_nights,
       m.nama                                    AS meal_plan,
       r.nama                                    AS room_type,
       s.nama                                    AS booking_source,
       st.nama                                   AS booking_status,
       b.lead_time,
       b.price,
       b.special_requests,
       b.car_parking
FROM booking b
JOIN dim_meal_plan      m  ON m.meal_plan_id = b.meal_plan_id
JOIN dim_room_type      r  ON r.room_type_id = b.room_type_id
JOIN dim_booking_source s  ON s.source_id    = b.source_id
JOIN dim_booking_status st ON st.status_id   = b.status_id;

CREATE OR REPLACE VIEW v_cancellation_by_source AS
SELECT s.nama                                            AS booking_source,
       COUNT(*)                                          AS bookings,
       SUM(CASE WHEN st.nama = 'Canceled' THEN 1 ELSE 0 END) AS cancelled,
       ROUND(100.0 * SUM(CASE WHEN st.nama = 'Canceled' THEN 1 ELSE 0 END)
             / COUNT(*), 1)                              AS cancel_pct,
       ROUND(AVG(b.lead_time))                           AS avg_lead_time
FROM booking b
JOIN dim_booking_source s  ON s.source_id  = b.source_id
JOIN dim_booking_status st ON st.status_id = b.status_id
GROUP BY s.nama
ORDER BY bookings DESC;

CREATE OR REPLACE VIEW v_revenue_by_room_type AS
SELECT r.nama                                            AS room_type,
       COUNT(*)                                          AS bookings,
       ROUND(AVG(b.price), 2)                            AS avg_price,
       ROUND(AVG(b.weekend_nights + b.week_nights), 1)   AS avg_nights,
       ROUND(SUM(b.price * (b.weekend_nights + b.week_nights)), 2) AS est_revenue
FROM booking b
JOIN dim_room_type r ON r.room_type_id = b.room_type_id
GROUP BY r.nama
ORDER BY est_revenue DESC;

-- Does booking further ahead predict cancellation? Lead time bucketed.
CREATE OR REPLACE VIEW v_lead_time_vs_cancellation AS
SELECT CASE
           WHEN b.lead_time < 7   THEN '0-6 days'
           WHEN b.lead_time < 30  THEN '7-29 days'
           WHEN b.lead_time < 90  THEN '30-89 days'
           ELSE '90+ days'
       END                                               AS lead_bucket,
       COUNT(*)                                          AS bookings,
       SUM(CASE WHEN st.nama = 'Canceled' THEN 1 ELSE 0 END) AS cancelled,
       ROUND(100.0 * SUM(CASE WHEN st.nama = 'Canceled' THEN 1 ELSE 0 END)
             / COUNT(*), 1)                              AS cancel_pct
FROM booking b
JOIN dim_booking_status st ON st.status_id = b.status_id
GROUP BY lead_bucket
ORDER BY MIN(b.lead_time);
