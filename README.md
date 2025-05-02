# Aplikasi Chat AI dengan Function Calling ke Elasticsearch

Aplikasi ini adalah sebuah chatbot berbasis web yang menggunakan Large Language Model (LLM) melalui Langchain. Chatbot ini memiliki kemampuan khusus untuk menjawab pertanyaan pengguna dengan mengambil data secara dinamis dari Elasticsearch menggunakan teknik *function calling*. Saat ini, chatbot dapat mengambil ringkasan data pesanan e-commerce dan informasi penerbangan.

## Fitur Utama

* **Antarmuka Chat Web:** Dibangun menggunakan Flask untuk interaksi pengguna yang mudah.
* **Agen AI:** Menggunakan Langchain untuk mengelola interaksi dengan LLM (dalam code ini mendukung OpenAI dan Azure OpenAI sebagai pilihan).
* **Function Calling:** Agen dapat secara otomatis memilih dan memanggil fungsi Python yang tepat berdasarkan pertanyaan pengguna:
    * `GetOrderSummary`: Mengambil ringkasan pesanan dari index Elasticsearch `kibana_sample_data_ecommerce` berdasarkan kata kunci (nama pelanggan, produk, kategori) dan filter hari.
    * `GetFlightInfo`: Mengambil informasi penerbangan dari index Elasticsearch `kibana_sample_data_flights` berdasarkan kata kunci (kota, bandara, maskapai, nomor penerbangan) dan filter hari dalam seminggu.
* **Memori Percakapan:** Agen mengingat konteks percakapan sebelumnya untuk interaksi yang lebih alami.
* **Integrasi Elasticsearch:** Terhubung langsung ke instance Elasticsearch untuk mengambil data *real-time*.
* **Konfigurasi Fleksibel:** Pengaturan koneksi (Elasticsearch, LLM) dikelola melalui variabel lingkungan (`.env`).

## Teknologi yang Digunakan

* **Backend:** Python 3.x
* **Web Framework:** Flask
* **Orkestrasi AI:** Langchain
* **LLM Provider:** OpenAI atau Azure OpenAI Service (dapat dikonfigurasi sesuai kebutuhan)
* **Database:** Elasticsearch
* **Lainnya:** `python-dotenv` (untuk environment variables)

## Struktur Proyek
```
.
├── .env             # File konfigurasi (DIBUAT MANUAL, JANGAN DI-COMMIT)
├── .gitignore       # File untuk mengabaikan file/folder tertentu oleh Git
├── agent.py         # Logika utama agen Langchain, inisialisasi LLM, tools, memori
├── app.py           # Aplikasi Flask (entry point, routing, session management)
├── elastic.py       # Fungsi untuk koneksi dan query ke Elasticsearch
├── index.html       # Template HTML untuk antarmuka chat
└── requirements.txt # Daftar dependensi Python
```
* **`app.py`**: Entry point aplikasi Flask, menangani request HTTP, manajemen sesi, dan merender UI.
* **`agent.py`**: Menginisialisasi LLM (OpenAI/Azure), mendefinisikan tools (fungsi Elasticsearch), memori percakapan, dan `AgentExecutor` Langchain.
* **`elastic.py`**: Berisi fungsi-fungsi (`get_order_summary`, `get_flight_info`) yang melakukan query ke Elasticsearch.
* **`index.html`**: Template frontend (antarmuka chat) yang ditampilkan ke pengguna.
* **`requirements.txt`**: Daftar semua pustaka Python yang dibutuhkan proyek.
* **`.env`**: File (yang harus Anda buat) untuk menyimpan kredensial dan konfigurasi sensitif seperti API keys, endpoint, dll. **PENTING: Jangan commit file ini ke Git.**

## Persiapan (Prerequisites)

Sebelum menjalankan aplikasi, pastikan Anda memiliki:

* Python 3.8 atau lebih baru.
* `pip` (package installer for Python).
* Akses ke instance Elasticsearch yang berisi index `kibana_sample_data_ecommerce` dan `kibana_sample_data_flights` (Anda bisa menggunakan data sample Kibana).
* Akun OpenAI API atau Akun Azure OpenAI Service beserta kredensialnya.
* Git (untuk mengkloning repositori).

## Instalasi dan Konfigurasi

1.  **Kloning Repositori:**
    ```bash
    git clone <URL-repositori-Anda>
    cd <nama-folder-repositori>
    ```

2.  **Buat Virtual Environment (Direkomendasikan):**
    ```bash
    python -m venv venv
    ```
    * **Windows:** `venv\Scripts\activate`
    * **macOS/Linux:** `source venv/bin/activate`

3.  **Instal Dependensi:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Buat dan Konfigurasi File `.env`:**
    Buat file bernama `.env` di root direktori proyek dan isi dengan konfigurasi berikut. **Isi nilai sesuai dengan setup Anda.**

    ```dotenv
    # Konfigurasi Elasticsearch
    ELASTICSEARCH_HOST="<URL_Elasticsearch_Anda_misal_http://localhost:9200>"
    ES_USER="<User_Elasticsearch_Anda_jika_ada>" # Kosongkan jika tidak pakai otentikasi
    ES_PASSWORD="<Password_Elasticsearch_Anda_jika_ada>" # Kosongkan jika tidak pakai otentikasi

    # --- Pilih SALAH SATU Konfigurasi LLM di bawah ini ---

    # Opsi 1: Konfigurasi OpenAI Standar
    # OPENAI_API_KEY="sk-..."

    # Opsi 2: Konfigurasi Azure OpenAI Service
    AZURE_OPENAI_ENDPOINT="<Endpoint_Azure_OpenAI_Anda>" # Contoh: [https://resource-name.openai.azure.com/](https://resource-name.openai.azure.com/)
    AZURE_OPENAI_API_KEY="<Kunci_API_Azure_OpenAI_Anda>"
    OPENAI_API_VERSION="<Versi_API_Azure_Anda>" # Contoh: 2024-02-15-preview
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="<Nama_Deployment_Model_Chat_Anda_di_Azure>"

    # --- Konfigurasi Flask ---
    # Ganti dengan kunci rahasia yang kuat dan acak untuk keamanan sesi
    FLASK_SECRET_KEY="<Kunci_Rahasia_Flask_Anda>"

    ```
    * **PENTING:** Isi hanya salah satu blok konfigurasi LLM (OpenAI *atau* Azure OpenAI), sesuai dengan provider yang Anda gunakan dan setup di `agent.py`.
    * Pastikan file `.env` ditambahkan ke `.gitignore` Anda agar tidak ter-commit.
    * Untuk `FLASK_SECRET_KEY`, Anda bisa menghasilkan kunci acak (misalnya menggunakan `python -c 'import os; print(os.urandom(24))'`).

## Menjalankan Aplikasi

Setelah semua konfigurasi selesai, jalankan aplikasi Flask:

```bash
python app.py
