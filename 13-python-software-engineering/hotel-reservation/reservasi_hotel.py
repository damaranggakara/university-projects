#Imports
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import csv

#Data pemesanan
reservations = []

#Booking
def book_reservation():
    name = name_entry.get()
    room = room_var.get()
    start_date = start_date_picker.get_date()
    end_date = end_date_picker.get_date()
    time_slot = time_slot_var.get()
    #Validasi input
    if not name or not room or not time_slot:
        messagebox.showerror("Input Error", "Semua kolom harus diisi!")
        return
    #Validasi pemesanan
    for reservation in reservations:
        if reservation['room'] == room and reservation['time_slot'] == time_slot and not (end_date < reservation['start_date'] or start_date > reservation['end_date']):
            messagebox.showerror("Ruang sudah dipesan!", "Ruang sudah dipesan pada slot dan tanggal yang dipilih.")
            return
    #Formulir input
    reservation = {
        'name': name,
        'room': room,
        'start_date': start_date,
        'end_date': end_date,
        'time_slot': time_slot
    }
    reservations.append(reservation)
    tree.insert('', 'end', values=(name, room, start_date, end_date, time_slot))
    #Reset input
    name_entry.delete(0, tk.END)
    room_var.set('')
    time_slot_var.set('')

#Menghapus pesanan
def delete_reservation():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showerror("Error", "Pilih baris untuk dihapus!")
        return
    #Hapus dari treeview
    tree.delete(selected_item)
    #hapus dari list pemesanan
    item = tree.item(selected_item)['values']
    reservations[:] = [r for r in reservations if not (r['name'] == item[0] and r['room'] == item[1] and str(r['start_date']) == item[2] and str(r['end_date']) == item[3] and r['time_slot'] == item[4])]

#Simpan pemesanan dalam csv
def export_to_csv():
    # Resolved relative to this file so the export works from any checkout.
    filepath = Path(__file__).parent / "Reservasi.csv"
    with open(filepath, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Nama Pemesan', 'Ruang', 'Tanggal Mulai', 'Tanggal Selesai', 'Waktu Slot'])
        for reservation in reservations:
            writer.writerow([reservation['name'], reservation['room'], reservation['start_date'], reservation['end_date'], reservation['time_slot']])
    messagebox.showinfo("Sukses", f"Data berhasil diekspor ke {filepath}")

#Setup aplikasi
root = tk.Tk()
root.title("Sistem Reservasi Ruang Meeting")

#Padding dan grid
main_frame = ttk.Frame(root, padding="5")
main_frame.grid(row=0, column=0, sticky=tk.NSEW)

#Form input
form_frame = ttk.LabelFrame(main_frame, text="Formulir Reservasi", padding="5")
form_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW)

#Input nama
ttk.Label(form_frame, text="Nama Pemesan").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
name_entry = ttk.Entry(form_frame, width=20)
name_entry.grid(row=0, column=1, padx=2, pady=2)

#Ruang meeting
ttk.Label(form_frame, text="Ruang Meeting").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
room_var = tk.StringVar(value='')  # Variabel untuk menyimpan pilihan Ruang Meeting
ttk.Radiobutton(form_frame, text="Ruang A", variable=room_var, value="Ruang A").grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)
ttk.Radiobutton(form_frame, text="Ruang B", variable=room_var, value="Ruang B").grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)
ttk.Radiobutton(form_frame, text="Ruang C", variable=room_var, value="Ruang C").grid(row=3, column=1, sticky=tk.W, padx=2, pady=2)

#Pop up kalender
ttk.Label(form_frame, text="Tanggal Mulai").grid(row=4, column=0, sticky=tk.W, padx=2, pady=2)
start_date_picker = DateEntry(form_frame, width=15)
start_date_picker.grid(row=4, column=1, padx=2, pady=2)
ttk.Label(form_frame, text="Tanggal Selesai").grid(row=5, column=0, sticky=tk.W, padx=2, pady=2)
end_date_picker = DateEntry(form_frame, width=15)
end_date_picker.grid(row=5, column=1, padx=2, pady=2)

#Waktu
ttk.Label(form_frame, text="Waktu Slot").grid(row=6, column=0, sticky=tk.W, padx=2, pady=2)
time_slot_var = tk.StringVar(value='')  # Variabel untuk menyimpan pilihan Waktu Slot
ttk.Radiobutton(form_frame, text="09:00 - 12:00", variable=time_slot_var, value="09:00 - 12:00").grid(row=6, column=1, sticky=tk.W, padx=2, pady=2)
ttk.Radiobutton(form_frame, text="13:00 - 16:00", variable=time_slot_var, value="13:00 - 16:00").grid(row=7, column=1, sticky=tk.W, padx=2, pady=2)
ttk.Radiobutton(form_frame, text="17:00 - 20:00", variable=time_slot_var, value="17:00 - 20:00").grid(row=8, column=1, sticky=tk.W, padx=2, pady=2)

#Pesan
book_button = ttk.Button(main_frame, text="Pesan", command=book_reservation)
book_button.grid(row=1, column=0, columnspan=2, pady=5)

#Tabel pemesanan
table_frame = ttk.LabelFrame(main_frame, text="Data Pemesanan", padding="5")
table_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW)
columns = ('Nama Pemesan', 'Ruang', 'Tanggal Mulai', 'Tanggal Selesai', 'Waktu Slot')
tree = ttk.Treeview(table_frame, columns=columns, show='headings')
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, minwidth=100, width=150, anchor=tk.CENTER)
tree.grid(row=0, column=0, sticky=tk.NSEW, padx=2, pady=2)

#Scrollbar
scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=1, sticky=tk.NS)

#Hapus export
button_frame = ttk.Frame(main_frame, padding="5")
button_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW)
delete_button = ttk.Button(button_frame, text="Hapus Pemesanan", command=delete_reservation)
delete_button.grid(row=0, column=0, padx=2)
export_button = ttk.Button(button_frame, text="Export", command=export_to_csv)
export_button.grid(row=0, column=1, padx=2)

#Grid
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
table_frame.grid_rowconfigure(0, weight=1)

#Loop aplikasi
root.mainloop()
