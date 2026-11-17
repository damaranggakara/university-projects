class Investasi:
    def roi(self, inv_awal, keuntungan):
        if inv_awal == 0:
            return "Modal awal tidak boleh nol."
        return ((keuntungan - inv_awal) / inv_awal) * 100

    def npv(self, inv_awal, arus_kas, suku_bunga):
        npv = -inv_awal
        for t, kas in enumerate(arus_kas):
            npv += kas / ((1 + suku_bunga) ** (t + 1))
        return npv

class LabaRugi:
    def labkot(self, pendapatan, biaya_pokok):
        return pendapatan - biaya_pokok

    def labber(self, labkot, biaya_operasional):
        return labkot - biaya_operasional
