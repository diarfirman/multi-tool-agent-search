import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, NotFoundError, ConnectionError
from typing import Optional # Pastikan Optional diimpor

load_dotenv()

# Inisialisasi koneksi Elasticsearch
es_host = os.getenv("ELASTICSEARCH_HOST")
es_user = os.getenv("ES_USER")
es_password = os.getenv("ES_PASSWORD")

if not es_host:
    raise ValueError("ELASTICSEARCH_HOST environment variable not set.")

try:
    es = Elasticsearch(
        hosts=[es_host],
        basic_auth=(es_user, es_password) if es_user and es_password else None,
        # Sesuaikan verify_certs jika menggunakan sertifikat self-signed atau tanpa SSL
        verify_certs=True,
        request_timeout=60
    )
    # Cek koneksi saat inisialisasi
    if not es.ping():
        raise ConnectionError("Failed to connect to Elasticsearch.")
    print("Successfully connected to Elasticsearch.") # Konfirmasi koneksi berhasil
except ConnectionError as ce:
     # Menangkap error koneksi spesifik
     print(f"Elasticsearch connection error: {ce}")
     raise ConnectionError(f"Error connecting to Elasticsearch: {ce}") from ce
except Exception as e:
    # Menangkap error umum lainnya saat inisialisasi
    print(f"An unexpected error occurred during Elasticsearch initialization: {e}")
    raise ConnectionError(f"Error connecting to Elasticsearch: {e}") from e


# --- Fungsi Order Summary (Parameter Spesifik, Tanpa Nested Query) ---
def get_order_summary(
    customer_name: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
    day: Optional[str] = None  # Tetap string ('Senin', 'Selasa', dll.)
) -> str:
    """
    Mengambil ringkasan pesanan dari Elasticsearch berdasarkan kriteria spesifik
    seperti nama pelanggan, nama produk, kategori produk, dan/atau hari.

    Args:
        customer_name (Optional[str]): Nama lengkap pelanggan (case-sensitive).
        product_name (Optional[str]): Nama produk yang dicari dalam pesanan.
        category (Optional[str]): Kategori produk yang dicari dalam pesanan.
        day (Optional[str]): Nama hari dalam seminggu (misal: 'Jumat', 'Monday').

    Returns:
        str: String ringkasan pesanan yang diformat atau pesan 'tidak ditemukan'.
    """
    # Memastikan setidaknya ada satu kriteria
    if not any([customer_name, product_name, category, day]):
        return "Mohon berikan setidaknya satu kriteria pencarian (nama pelanggan, produk, kategori, atau hari)."

    # Filter di level utama
    top_level_filters = []
    criteria_list = [] # Untuk deskripsi di output

    if customer_name:
        # Menggunakan term untuk kecocokan eksak (case-sensitive) pada field keyword
        top_level_filters.append({"term": {"customer_full_name.keyword": customer_name}})
        criteria_list.append(f"pelanggan '{customer_name}'")
    if day:
        # Pastikan nilai 'day' cocok dengan data di field 'day_of_week'
        top_level_filters.append({"term": {"day_of_week": day}})
        criteria_list.append(f"pada hari '{day}'")
    if product_name:
        # Menggunakan match untuk pencarian teks pada field produk
        top_level_filters.append({"match": {"products.product_name": product_name}})
        criteria_list.append(f"produk '{product_name}'")
    if category:
        # Menggunakan term untuk kecocokan eksak pada field kategori (asumsi keyword)
        top_level_filters.append({"term": {"products.category": category}})
        criteria_list.append(f"kategori '{category}'")

    if not top_level_filters:
         # Seharusnya tidak terjadi karena cek di awal, tapi sebagai fallback
         return "Tidak ada kriteria pencarian valid yang bisa digunakan."

    # Bangun query Elasticsearch akhir
    query = {
        "size": 50, # Jumlah maksimal pesanan yang ditampilkan
        "query": {
            "bool": {
                "filter": top_level_filters # Menggabungkan semua filter
            }
        },
         "sort": [
             # Urutkan berdasarkan tanggal pesanan (pastikan field 'order_date' ada)
            {"order_date": {"order": "desc"}}
        ]
    }

    # Lakukan pencarian
    try:
        # print(f"Debug: Elasticsearch Order Query: {query}") # Aktifkan untuk debug
        res = es.search(index="kibana_sample_data_ecommerce", body=query)
    except NotFoundError:
        return "Error: Index 'kibana_sample_data_ecommerce' tidak ditemukan."
    except ConnectionError as e:
        # Error koneksi saat pencarian
        print(f"Connection error during order search: {e}")
        return "Maaf, terjadi masalah koneksi saat mengambil data pesanan."
    except Exception as e:
        # Menangkap error lain saat pencarian (misal: mapping error, query error)
        print(f"Error searching orders in Elasticsearch: {e}")
        print(f"Query causing error: {query}")
        # Berikan pesan error yang lebih spesifik jika memungkinkan
        error_type = getattr(e, 'error', 'unknown')
        error_reason = getattr(e, 'info', {}).get('error', {}).get('root_cause', [{}])[0].get('reason', str(e))
        return f"Maaf, terjadi kesalahan ({error_type}) saat mengambil data pesanan: {error_reason}"

    orders = res['hits']['hits']
    criteria_str = " dan ".join(criteria_list) if criteria_list else "yang diminta"

    if not orders:
        return f"Tidak ditemukan pesanan {criteria_str}."

    # --- Pemformatan Output ---
    summary_lines = []
    order_count = 1
    summary_lines.append(f"Berikut ini adalah ringkasan pembelian {criteria_str}:")

    for order in orders:
        o = order['_source']
        # Ambil tanggal dari field 'order_date', potong waktunya
        order_info_date = "N/A"
        if o.get('order_date'):
            order_info_date = o.get('order_date')[:10] # Ambil YYYY-MM-DD
        elif o.get('day_of_week'):
            order_info_date = o.get('day_of_week') # Fallback ke hari jika tanggal tidak ada

        # Format detail produk dalam pesanan
        items = []
        total_order_value = 0
        for p in o.get('products', []):
            price = p.get('base_price', 0) # Gunakan base_price atau price
            quantity = p.get('quantity', 1)
            items.append(
                f"  * {quantity}x {p.get('product_name', 'N/A')} ({p.get('category', 'N/A')}) - EUR {price:.2f}"
            )
            total_order_value += price * quantity

        items_str = "\n".join(items) if items else "  (Detail produk tidak tersedia)"

        summary_lines.append(
            f"{order_count}. Order #{o.get('order_id', 'N/A')} oleh {o.get('customer_full_name', 'N/A')} "
            f"pada {order_info_date} (Total: EUR {o.get('total_unique_products', '?')} produk senilai EUR {total_order_value:.2f}):\n{items_str}"
        )
        order_count += 1

    return "\n".join(summary_lines)


# --- Fungsi Flight Info (Parameter Spesifik) ---
def get_flight_info(
    origin_city: Optional[str] = None,
    destination_city: Optional[str] = None,
    carrier: Optional[str] = None,
    flight_num: Optional[str] = None,
    day_of_week: Optional[int] = None # Angka 0-6
) -> str:
    """
    Mengambil informasi penerbangan dari Elasticsearch berdasarkan kriteria spesifik.

    Args:
        origin_city (Optional[str]): Nama kota asal.
        destination_city (Optional[str]): Nama kota tujuan.
        carrier (Optional[str]): Nama maskapai penerbangan.
        flight_num (Optional[str]): Nomor penerbangan.
        day_of_week (Optional[int]): Angka hari dalam seminggu (0=Senin, ..., 6=Minggu).

    Returns:
        str: String ringkasan informasi penerbangan atau pesan 'tidak ditemukan'.
    """
    # Memastikan setidaknya ada satu kriteria
    if not any([origin_city, destination_city, carrier, flight_num, day_of_week is not None]):
        return "Mohon berikan setidaknya satu kriteria pencarian penerbangan (kota asal/tujuan, maskapai, nomor penerbangan, atau hari)."

    filters = [] # List untuk filter Elasticsearch
    criteria_list = [] # Untuk deskripsi di output

    # Tambahkan filter berdasarkan parameter yang ada
    if origin_city:
        filters.append({"term": {"OriginCityName": origin_city}})
        criteria_list.append(f"asal '{origin_city}'")
    if destination_city:
        filters.append({"term": {"DestCityName": destination_city}})
        criteria_list.append(f"tujuan '{destination_city}'")
    if carrier:
        filters.append({"term": {"Carrier": carrier}})
        criteria_list.append(f"maskapai '{carrier}'")
    if flight_num:
        filters.append({"term": {"FlightNum": flight_num}}) # Asumsi keyword
        criteria_list.append(f"nomor penerbangan '{flight_num}'")
    if day_of_week is not None:
        if 0 <= day_of_week <= 6:
            filters.append({"term": {"dayOfWeek": day_of_week}})
            days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            try:
                criteria_list.append(f"pada hari {days[day_of_week]}")
            except IndexError:
                criteria_list.append(f"pada hari ke-{day_of_week}")
        else:
            print(f"Peringatan: Nilai day_of_week ({day_of_week}) tidak valid. Filter hari diabaikan.")

    if not filters:
         return "Tidak ada kriteria pencarian valid yang bisa digunakan."

    # Bangun query Elasticsearch
    query = {
        "size": 10, # Batasi jumlah hasil
        "query": {
            "bool": {
                "filter": filters
            }
        },
        "sort": [
             {"timestamp": {"order": "desc"}} # Urutkan penerbangan terbaru dulu
         ]
    }

    # Lakukan pencarian
    try:
        # print(f"Debug: Elasticsearch Flight Query: {query}") # Aktifkan untuk debug
        res = es.search(index="kibana_sample_data_flights", body=query)
    except NotFoundError:
        return "Error: Index 'kibana_sample_data_flights' tidak ditemukan."
    except ConnectionError as e:
         print(f"Connection error during flight search: {e}")
         return "Maaf, terjadi masalah koneksi saat mengambil data penerbangan."
    except Exception as e:
        print(f"Error searching flights in Elasticsearch: {e}")
        print(f"Query causing error: {query}")
        error_type = getattr(e, 'error', 'unknown')
        error_reason = getattr(e, 'info', {}).get('error', {}).get('root_cause', [{}])[0].get('reason', str(e))
        return f"Maaf, terjadi kesalahan ({error_type}) saat mengambil data penerbangan: {error_reason}"

    flights = res['hits']['hits']
    criteria_str = " dan ".join(criteria_list) if criteria_list else "yang diminta"

    if not flights:
        return f"Tidak ditemukan penerbangan {criteria_str}."

    # --- Pemformatan Output ---
    summary_lines = []
    flight_count = 1
    summary_lines.append(f"Berikut adalah informasi penerbangan {criteria_str}:")
    summary_lines.append("-" * 30)

    for flight in flights:
        f = flight['_source']
        timestamp_str = f.get('timestamp', 'N/A').replace('T', ' ') if f.get('timestamp') else 'N/A'
        status = "Tepat Waktu"
        if f.get('Cancelled', False): status = "Dibatalkan"
        elif f.get('FlightDelay', False): status = f"Delay ({f.get('FlightDelayType', 'N/A')})"

        details = [
             f"  Nomor: {f.get('FlightNum', 'N/A')}",
             f"  Maskapai: {f.get('Carrier', 'N/A')}",
             f"  Asal: {f.get('OriginCityName', 'N/A')} ({f.get('OriginAirportID', 'N/A')}) - {f.get('Origin', 'N/A')}",
             f"  Tujuan: {f.get('DestCityName', 'N/A')} ({f.get('DestAirportID', 'N/A')}) - {f.get('Dest', 'N/A')}",
             f"  Waktu Keberangkatan (UTC): {timestamp_str}",
             f"  Durasi: {f.get('FlightTimeMin', 0):.1f} menit",
             f"  Jarak: {f.get('DistanceKilometers', 0):.1f} km",
             f"  Harga Tiket Rata-rata: ${f.get('AvgTicketPrice', 0):.2f}",
             f"  Status: {status}",
        ]
        summary_lines.append(f"{flight_count}. Penerbangan {f.get('FlightNum', 'N/A')}:")
        summary_lines.extend(details)
        summary_lines.append("-" * 30)
        flight_count += 1

    return "\n".join(summary_lines)
