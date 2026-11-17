#imports
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from statistics import mean, median, mode, stdev, variance
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

#Analisis deskriptif
def analisis_deskriptif():
    try:
        #Input data berdasarkan koma
        data_input = entry.get()
        data = list(map(float, data_input.split(',')))

        #Perhitungan analisis deskriptif
        rata2 = mean(data)
        median_value = median(data)
        modus_value = mode(data)
        kuartil1 = np.percentile(data, 25)
        kuartil3 = np.percentile(data, 75)
        minimum = min(data)
        maksimum = max(data)
        simpangan_baku = stdev(data)
        varians_value = variance(data)

        #Hapus data lama dari tabel
        for row in table.get_children():
            table.delete(row)

        #Hasil analisis dalam tabel
        table.insert('', 'end', values=("Rata-rata", f"{rata2:.2f}"))
        table.insert('', 'end', values=("Median", f"{median_value:.2f}"))
        table.insert('', 'end', values=("Modus", f"{modus_value:.2f}"))
        table.insert('', 'end', values=("Kuartil 1", f"{kuartil1:.2f}"))
        table.insert('', 'end', values=("Kuartil 3", f"{kuartil3:.2f}"))
        table.insert('', 'end', values=("Nilai Minimum", f"{minimum:.2f}"))
        table.insert('', 'end', values=("Nilai Maksimum", f"{maksimum:.2f}"))
        table.insert('', 'end', values=("Simpangan Baku", f"{simpangan_baku:.2f}"))
        table.insert('', 'end', values=("Varians", f"{varians_value:.2f}"))

    except ValueError:
        messagebox.showerror("Input Error", "Harap masukkan data numerik yang valid.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

#Diagram batang
def tampilkan_diagram_batang():
    try:
        #Input data berdasarkan koma
        data_input = entry.get()
        data = list(map(float, data_input.split(',')))

        #Hitung frekuensi
        nilai_unik, frekuensi = np.unique(data, return_counts=True)

        #Visualisasi diagram
        fig, ax = plt.subplots()
        ax.bar(nilai_unik, frekuensi, color='skyblue')
        ax.set_xlabel('Nilai Data')
        ax.set_ylabel('Frekuensi Kemunculan')
        ax.set_title('Diagram Batang Frekuensi Data')
        ax.grid(True, linestyle='--', alpha=0.7)

        #Pop up window
        new_window = tk.Toplevel(root)
        new_window.title("Diagram Batang")
        new_window.geometry("600x400")

        # Membuat canvas buat diagram
        canvas = FigureCanvasTkAgg(fig, master=new_window)
        canvas.draw()

        #Widget dan pengaturan layout
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        #Toolbar
        toolbar_frame = NavigationToolbar2Tk(canvas, new_window)
        toolbar_frame.update()

    except ValueError:
        messagebox.showerror("Input Error", "Harap masukkan data numerik yang valid.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

#Pengaturan GUI
root = tk.Tk()
root.title("Aplikasi Analisis Deskriptif Statistik")
root.geometry("800x300")

#Warna UI
bg_color = "#f0f0f0"
button_color = "#4682B4"
text_color = "#ffffff"
root.configure(bg=bg_color)

#Pengaturan layout
main_frame = tk.Frame(root, padx=20, pady=20, bg=bg_color)
main_frame.pack(fill=tk.BOTH, expand=True)

#Input data dan tombol
input_frame = tk.Frame(main_frame, bg=bg_color)
input_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

#Label dan input field
label = tk.Label(input_frame, text="Masukkan data numerik (pisahkan dengan koma):", bg=bg_color)
label.pack(anchor='w', pady=5)
entry = tk.Entry(input_frame, width=40)
entry.pack(pady=5)

#Tombol analisis deskriptif
btn_analisis = tk.Button(input_frame, text="Analisis Deskriptif", command=analisis_deskriptif,
                         bg=button_color, fg=text_color)
btn_analisis.pack(pady=10)

#Tombol diagram batang
btn_diagram = tk.Button(input_frame, text="Diagram Batang", command=tampilkan_diagram_batang,
                        bg=button_color, fg=text_color)
btn_diagram.pack(pady=5)

#Tabel analisis
table_frame = tk.Frame(main_frame, bg=bg_color)
table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
columns = ('Deskripsi', 'Nilai')
table = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
table.heading('Deskripsi', text='Deskripsi')
table.heading('Nilai', text='Nilai')

#Scrollbar bila diperlukan
scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
table.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
table.pack(fill=tk.BOTH, expand=True)

#Isi tabel
deskripsi_awal = [
    "Rata-rata", "Median", "Modus", "Kuartil 1", 
    "Kuartil 3", "Nilai Minimum", "Nilai Maksimum", 
    "Simpangan Baku", "Varians"
]
for deskripsi in deskripsi_awal:
    table.insert('', 'end', values=(deskripsi, ''))

#Eksekusi aplikasi
root.mainloop()
