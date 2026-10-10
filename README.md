# Satisfying Relaxation – generator video YouTube (long)

Video 8 menit 1080p/30fps, **100% dibuat dari kode** (visual + audio), dirender di GitHub Actions.
Tanpa footage/musik eksternal.

## Isi video (4 scene × 2 menit, crossfade 3 dtk)
| Scene | Deskripsi |
|---|---|
| Sunset Waves | gelombang berlapis + matahari berdenyut |
| Pendulum Wave | 21 bola, pola menyatu lagi tiap 60 dtk |
| Bouncing Orbs | orb memantul + ring riak; **bell berbunyi tepat saat orb mendarat** |
| Glowing Spirograph | dua spirograph morphing dengan glow |

Audio: pad ambient (Cmaj9→Am9→Fmaj7→G6/9), suara ombak (filtered noise), bell pentatonik + reverb.

## Pakai di GitHub
1. Buat repo, push semua file ini.
2. **Actions → Render Satisfying Relaxation → Run workflow** (atur menit / resolusi / fps / seed).
3. Hasil (mp4, thumbnail.jpg, metadata.json) ada di **Artifacts** run tersebut (disimpan 7 hari).

Perkiraan waktu runner publik (4 core): ±10–20 menit untuk 8 menit 1080p.
Repo private (2 core) bisa 2× lebih lama; naikkan `--preset` ke `veryfast` bila perlu.

## Jalan lokal
```bash
pip install -r requirements.txt        # butuh ffmpeg terpasang
python -m generator.render --out out
# tes cepat:
SR_MINUTES=0.5 SR_HEIGHT=360 python -m generator.render --out out --preset ultrafast
```
Env: `SR_MINUTES`, `SR_HEIGHT` (720/1080/1440), `SR_FPS`, `SR_SEED` (variasi warna & nada).

## Upload otomatis ke YouTube (opsional)
1. Google Cloud Console → aktifkan **YouTube Data API v3** → buat OAuth client (Desktop app).
2. Dapatkan *refresh token* dengan scope `https://www.googleapis.com/auth/youtube.upload`
   (mis. lewat OAuth Playground, centang "Use your own OAuth credentials").
3. Repo → Settings → Secrets → tambahkan `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
4. Jalankan workflow dengan `upload = true`.

Catatan: project API yang belum lolos audit Google membuat video upload terkunci **private**
(ubah manual di YouTube Studio). Pertimbangkan juga mengunggah manual dari Artifact.

## Tips channel
- Ganti `SR_SEED` tiap video agar warna & nada berbeda (hindari kesan konten massal/repetitif).
- Tambah scene baru: buat fungsi `scene_xxx(s) -> Image` di `scenes.py` lalu daftarkan di `SCENES`
  (ubah `N_SCENES` di `config.py`).
- Untuk video lebih panjang (1–10 jam), cukup naikkan `minutes`; render paralel per-chunk 15 detik.
