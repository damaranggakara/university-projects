#impor file
from ekonomi.keuangan import Investasi, LabaRugi
from ekonomi.pajak import Pajak

#investasi
investasi = Investasi()
inv_awal = 100000
keuntungan = 120000
roi = investasi.roi(inv_awal, keuntungan)
print(f"Return on Investment (ROI): {roi}%")

#pajak hasil
pajak = Pajak()
pendapatan_pajak = 200000 
persen_pajak = 10 
pajak_hasil = pajak.pajak_hasil(pendapatan_pajak, persen_pajak)
print(f"Pajak Hasil: {pajak_hasil}")

