# Impor modul yang diperlukan dari Flask
from flask import Flask, render_template, request, session
# Impor fungsi chat dari file agent Anda
from agent import chat_with_agent
# Impor os untuk menghasilkan secret key (atau muat dari env)
import os

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- Konfigurasi Sesi Flask (SANGAT PENTING) ---
# Flask membutuhkan 'secret_key' untuk mengelola sesi pengguna secara aman.
# Ganti ini dengan kunci rahasia Anda sendiri yang kuat dan sulit ditebak.
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24)) # Coba ambil dari env atau buat acak

# ---------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def index():
    # Inisialisasi riwayat obrolan dalam sesi jika belum ada
    if 'chat_history' not in session:
        session['chat_history'] = [] # Buat list kosong untuk menyimpan pesan

    # Tangani permintaan POST (ketika pengguna mengirim pesan)
    if request.method == 'POST':
        user_question = request.form.get('question')

        if user_question: # Pastikan ada pertanyaan
            # Panggil agen Langchain Anda untuk mendapatkan respons
            response_text = chat_with_agent(user_question)

            # Tambahkan pertanyaan pengguna ke riwayat sesi
            session['chat_history'].append({'type': 'user', 'text': user_question})
            # Tambahkan respons AI ke riwayat sesi
            session['chat_history'].append({'type': 'ai', 'text': response_text})

            # Tandai sesi sebagai termodifikasi
            session.modified = True

    # Render template HTML, kirimkan seluruh riwayat obrolan dari sesi
    return render_template('index.html', chat_history=session.get('chat_history', []))

# Jalankan aplikasi
if __name__ == '__main__':
    # Gunakan host='0.0.0.0' agar bisa diakses dari luar Docker/VM jika perlu
    # debug=True hanya untuk pengembangan
    app.run(debug=True, host='0.0.0.0', port=5000)
