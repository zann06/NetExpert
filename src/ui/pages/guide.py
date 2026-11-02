"""User guide explaining the expert-system concepts and app operation."""

from __future__ import annotations

import streamlit as st

from .. import components as c


def render() -> None:
    c.page_head(
        "Panduan",
        "Penjelasan konsep inference engine dan cara mengoperasikan NetExpert.",
    )

    tab_concepts, tab_resolution, tab_truth, tab_usage = st.tabs(
        ["Metode Inferensi", "Conflict Resolution", "TRUE / FALSE", "Cara Pakai"]
    )

    with tab_concepts:
        _render_inference_methods()
    with tab_resolution:
        _render_conflict_resolution()
    with tab_truth:
        _render_truth()
    with tab_usage:
        _render_usage()


def _render_inference_methods() -> None:
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-card-title">Forward Chaining — data-driven</div>'
        '<div class="nx-card-sub">Mulai dari fakta, bergerak menuju kesimpulan.</div>'
        "<ol style='font-size:0.85rem;line-height:1.75;color:#334155;margin:0.4rem 0 0 1rem;padding:0'>"
        "<li>Muat fakta awal ke working memory.</li>"
        "<li>Evaluasi setiap kondisi IF pada setiap aturan yang belum refractory.</li>"
        "<li>Tandai kondisi TRUE jika fakta ada, FALSE jika tidak ada.</li>"
        "<li>Aturan READY bila kondisi IF memenuhi operatornya: semua TRUE untuk AND, minimal satu TRUE untuk OR; kumpulkan ke conflict set.</li>"
        "<li>Pilih satu aturan dengan salience → spesifisitas → nomor aturan.</li>"
        "<li>Tembakkan aturan, tambahkan kesimpulan ke working memory.</li>"
        "<li>Ulangi sampai conflict set kosong.</li>"
        "</ol></div>"
    )

    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-card-title">Backward Chaining — goal-driven</div>'
        '<div class="nx-card-sub">Mulai dari goal, mundur menuju fakta pendukung.</div>'
        "<ol style='font-size:0.85rem;line-height:1.75;color:#334155;margin:0.4rem 0 0 1rem;padding:0'>"
        "<li>Terima goal dari pengguna.</li>"
        "<li>Jika goal ada di fakta awal, goal PROVEN.</li>"
        "<li>Cari aturan yang THEN-nya sama dengan goal (kandidat).</li>"
        "<li>Urutkan kandidat dengan conflict resolution.</li>"
        "<li>Ubah setiap kondisi IF menjadi subgoal dan buktikan secara rekursif.</li>"
        "<li>Jika kondisi IF memenuhi operator aturan (semua untuk AND, minimal satu untuk OR), goal PROVEN.</li>"
        "<li>Jika semua kandidat gagal, goal UNPROVEN.</li>"
        "<li>Deteksi siklus agar rekursi berhenti.</li>"
        "</ol></div>"
    )

    c.banner(
        "blue",
        "Perbedaan kunci",
        "Forward chaining menjawab 'fakta apa yang bisa saya simpulkan?'. "
        "Backward chaining menjawab 'apakah goal ini dapat dibuktikan, dan bagaimana?'.",
    )


def _render_conflict_resolution() -> None:
    c.section_title(
        "Urutan prioritas",
        "Diterapkan secara berurutan; level berikutnya hanya dipakai jika terjadi seri.",
    )
    c.steps(
        [
            ("01", "Salience", "Nilai lebih tinggi menang. 1 = Rendah, 2 = Sedang, 3 = Tinggi, 4 = Tertinggi."),
            ("02", "Spesifisitas", "Jika salience sama, aturan dengan jumlah kondisi IF lebih banyak menang."),
            ("03", "Nomor aturan", "Jika masih sama, nomor aturan lebih kecil menang secara numerik (R2 sebelum R10)."),
        ]
    )

    st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-card-title">Contoh dari assignment</div>'
        '<div class="nx-card-sub">Iterasi 1 pada skenario default.</div>'
        '<div class="nx-table-wrap"><table class="nx-table"><thead><tr>'
        "<th>Aturan</th><th>Salience</th><th>Spesifisitas</th><th>Hasil</th></tr></thead><tbody>"
        "<tr><td><strong>R5</strong></td><td>2 (Sedang)</td><td>1</td>"
        "<td>" + c.badge("SELECTED", "green") + " salience lebih tinggi</td></tr>"
        "<tr><td><strong>R1</strong></td><td>1 (Rendah)</td><td>1</td>"
        "<td>" + c.badge("READY BUT NOT SELECTED", "amber") + "</td></tr>"
        "</tbody></table></div>"
        "</div>"
    )

    c.banner(
        "amber",
        "Refractoriness",
        "Setiap aturan hanya boleh fired satu kali dalam satu eksekusi. Setelah fired, "
        "aturan keluar dari conflict set sampai run berikutnya. Jika kesimpulannya sudah "
        "ada di working memory, aturan tetap dicatat fired tetapi fakta tidak diduplikasi.",
    )


def _render_truth() -> None:
    c.section_title(
        "Status yang wajib dibedakan",
        "Warna selalu disertai label teks pada tree dan tabel.",
    )
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-table-wrap"><table class="nx-table"><thead><tr>'
        "<th>Status</th><th>Arti</th><th>Tampilan</th></tr></thead><tbody>"
        "<tr><td>" + c.badge("TRUE", "green") + "</td>"
        "<td>Fakta kondisi ditemukan di working memory.</td><td>Hijau</td></tr>"
        "<tr><td>" + c.badge("FALSE", "red") + "</td>"
        "<td>Fakta kondisi tidak ditemukan.</td><td>Merah</td></tr>"
        "<tr><td>" + c.badge("READY", "amber") + "</td>"
        "<td>Kondisi IF memenuhi operator aturan (semua TRUE untuk AND / minimal satu TRUE untuk OR).</td><td>Amber</td></tr>"
        "<tr><td>" + c.badge("NOT READY", "red") + "</td>"
        "<td>Kondisi IF tidak memenuhi operator aturan — aturan tidak boleh fired.</td><td>Merah</td></tr>"
        "<tr><td>" + c.badge("FIRED", "green") + "</td>"
        "<td>Aturan dipilih dan ditembakkan.</td><td>Hijau</td></tr>"
        "<tr><td>" + c.badge("READY BUT NOT SELECTED", "amber") + "</td>"
        "<td>Kondisi IF memenuhi operator tetapi kalah conflict resolution. Berbeda dari NOT READY.</td><td>Amber</td></tr>"
        "<tr><td>" + c.badge("REFRACTORY", "gray") + "</td>"
        "<td>Sudah fired pada run ini sehingga tidak dievaluasi ulang.</td><td>Abu-abu</td></tr>"
        "</tbody></table></div>"
        "</div>"
    )

    c.banner(
        "blue",
        "Mengapa perbedaan ini penting?",
        "Aturan yang gagal karena kondisi FALSE menunjukkan fakta yang belum tersedia, "
        "sedangkan READY BUT NOT SELECTED menunjukkan aturan tersebut sebenarnya valid "
        "tetapi kalah prioritas. Keduanya membutuhkan penjelasan yang berbeda.",
    )


def _render_usage() -> None:
    c.section_title("Alur penggunaan", "Lima langkah untuk menjalankan dan mengaudit inferensi.")
    c.steps(
        [
            ("1", "Atur fakta awal", "Buka Diagnosis, pilih fakta dari katalog atau tambahkan fakta manual."),
            ("2", "Pilih metode", "Forward Chaining untuk enumerasi kesimpulan; Backward Chaining untuk membuktikan goal."),
            ("3", "Jalankan", "Tekan Jalankan inferensi. Hasil, conflict set, dan iteration log muncul."),
            ("4", "Audit", "Buka setiap iterasi untuk melihat TRUE/FALSE setiap kondisi dan alasan pemilihan aturan."),
            ("5", "Visualisasikan", "Buka Inference Tree dan gunakan filter untuk menelusuri cabang berhasil atau gagal."),
        ]
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-card-title">Contoh goal backward chaining</div>'
        '<div class="nx-card-sub">Gunakan fakta default dan goal berikut.</div>'
        '<div style="margin:0.3rem 0">'
        '<span class="nx-chip blue">Goal: Lapor ke Provider</span>'
        '<span class="nx-chip green">R4</span>'
        '<span class="nx-chip blue">Gangguan Provider</span>'
        '<span class="nx-chip green">R5</span>'
        '<span class="nx-chip blue">Perangkat Lain Juga Offline</span>'
        '<span class="nx-chip green">Tagihan Sudah Dibayar</span>'
        "</div>"
        '<div class="nx-eval-reason">R4 membutuhkan Gangguan Provider dan Tagihan Sudah Dibayar. '
        "Gangguan Provider dibuktikan oleh R5 dari fakta Perangkat Lain Juga Offline, "
        "sedangkan Tagihan Sudah Dibayar sudah ada di fakta awal. Karena itu goal PROVEN.</div>"
        "</div>"
    )

    c.banner(
        "blue",
        "Tips audit",
        "Jika hasil tidak sesuai harapan, periksa urutan: (1) fakta awal, "
        "(2) kondisi IF yang FALSE, (3) salience dan spesifisitas aturan, "
        "(4) aturan yang sudah refractory.",
    )