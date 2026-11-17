class Pajak:
    def pajak_hasil(self, pendapatan, persen_pajak):
        if persen_pajak < 0:
            raise ValueError("Persentase pajak tidak boleh negatif.")
        return pendapatan * (persen_pajak / 100)

    def ppn(self, penjualan, tarif_ppn):
        if tarif_ppn < 0:
            raise ValueError("Tarif PPN tidak boleh negatif.")
        return penjualan * (tarif_ppn / 100)

