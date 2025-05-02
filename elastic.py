import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, NotFoundError

load_dotenv()

# Inisialisasi koneksi Elasticsearch (sama seperti sebelumnya)
es_host = os.getenv("ELASTICSEARCH_HOST")
es_user = os.getenv("ES_USER")
es_password = os.getenv("ES_PASSWORD")

if not es_host:
    raise ValueError("ELASTICSEARCH_HOST environment variable not set.")

try:
    es = Elasticsearch(
        hosts=[es_host],
        basic_auth=(es_user, es_password) if es_user and es_password else None,
        verify_certs=True,
        request_timeout=60
    )
    if not es.ping():
        raise ConnectionError("Failed to connect to Elasticsearch.")
except Exception as e:
    raise ConnectionError(f"Error connecting to Elasticsearch: {e}") from e


# --- Fungsi Dimodifikasi: Tanpa Nested Query ---
def get_order_summary(query_string: str, day: str = None) -> str:
    """
    Mengambil ringkasan pesanan dari Elasticsearch menggunakan multi-match query
    langsung pada nama pelanggan, nama produk, dan kategori (TANPA nested query),
    dengan filter hari opsional.

    Args:
        query_string (str): Teks pencarian umum (nama, produk, kategori).
        day (str, optional): Hari dalam seminggu untuk filter tambahan. Defaults to None.

    Returns:
        str: String ringkasan pesanan yang diformat atau pesan 'tidak ditemukan'.
    """
    if not query_string:
        return "Mohon berikan kata kunci pencarian (nama pelanggan, produk, atau kategori)."

    query = {
        "size": 50,
        "query": {
            "bool": {
                "must": [
                    # --- Multi-Match Langsung (Tanpa Nested) ---
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": [
                                "customer_full_name^2", # Beri boost jika cocok nama pelanggan
                                "products.product_name",
                                "products.category"
                                # Tambahkan field lain jika perlu, misal "products.description"
                            ],
                            "type": "best_fields" # Atau tipe lain yang sesuai
                        }
                    }
                    # --- Akhir Multi-Match Langsung ---
                ],
                "filter": [] # Filter context untuk hari
            }
        }
    }

    # Tambahkan filter hari jika disediakan
    if day:
        query["query"]["bool"]["filter"].append(
            {"term": {"day_of_week": day}}
        )

    # Hapus list 'filter' jika kosong
    if not query["query"]["bool"]["filter"]:
        del query["query"]["bool"]["filter"]

    # Lakukan pencarian
    try:
        # print(f"Elasticsearch Query (Workaround): {query}") # Uncomment untuk debug
        res = es.search(index="kibana_sample_data_ecommerce", body=query)
    except NotFoundError:
        return "Error: Index 'kibana_sample_data_ecommerce' tidak ditemukan."
    except ConnectionError as e:
         print(f"Connection error during search: {e}")
         return "Maaf, terjadi masalah koneksi saat mengambil data pesanan."
    # Tangani error spesifik dari multi_match jika field tidak ada/salah mapping
    except Exception as e:
        # Periksa apakah ini error terkait field tidak ditemukan di multi_match
        if 'No keyword/text fields found' in str(e):
             print(f"Mapping Error: Pastikan field di multi_match ada dan bertipe teks/keyword. Error: {e}")
             return "Maaf, terjadi kesalahan konfigurasi pencarian. Field tidak ditemukan."
        print(f"Error searching Elasticsearch: {e}")
        print(f"Query causing error: {query}")
        return "Maaf, terjadi kesalahan tak terduga saat mengambil data pesanan."

    orders = res['hits']['hits']

    if not orders:
        return f"Tidak ditemukan pesanan yang cocok dengan '{query_string}'" + (f" pada hari '{day}'." if day else ".")

    # --- Pemformatan Output (Sama seperti sebelumnya) ---
    summary_lines = []
    order_count = 1

    criteria_str = f"yang cocok dengan '{query_string}'" + (f" pada hari {day}" if day else "")
    summary_lines.append(f"Berikut ini adalah ringkasan pembelian {criteria_str}:")

    for order in orders:
        o = order['_source']
        items = [
            f"  * {p.get('quantity', '?')}x {p.get('product_name', 'N/A')} (EUR {p.get('price', 'N/A')})"
            for p in o.get('products', [])
        ]
        items_str = "\n".join(items)

        summary_lines.append(
            f"{order_count}. Order #{o.get('order_id', 'N/A')} oleh {o.get('customer_full_name', 'N/A')} "
            f"pada {o.get('day_of_week', 'N/A')}:\n{items_str}"
        )
        order_count += 1

    return "\n".join(summary_lines)

# --- FUNGSI BARU: Untuk Mengambil Informasi Penerbangan ---
def get_flight_info(query_string: str, day_of_week: int = None) -> str:
    """
    Mengambil informasi penerbangan dari Elasticsearch berdasarkan kata kunci
    (kota asal/tujuan, bandara, maskapai, nomor penerbangan) dengan filter hari opsional.

    Args:
        query_string (str): Teks pencarian umum terkait penerbangan.
        day_of_week (int, optional): Angka hari dalam seminggu (0=Senin, ..., 4=Jumat, ..., 6=Minggu)
                                     berdasarkan data Elasticsearch. Defaults to None.

    Returns:
        str: String ringkasan informasi penerbangan yang diformat atau pesan 'tidak ditemukan'.
    """
    if not query_string:
        return "Mohon berikan kata kunci pencarian penerbangan (kota, bandara, maskapai, atau nomor penerbangan)."

    # Field yang relevan untuk pencarian multi_match
    search_fields = [
        "OriginCityName^2",   # Beri bobot lebih pada nama kota
        "DestCityName^2",
        "Origin",             # Nama bandara asal
        "Dest",               # Nama bandara tujuan
        "Carrier",            # Nama maskapai
        "FlightNum^3"         # Beri bobot paling tinggi pada nomor penerbangan
    ]

    query = {
        "size": 10,  # Batasi jumlah hasil agar tidak terlalu panjang
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": search_fields,
                            "type": "best_fields" # Cari kecocokan terbaik di salah satu field
                        }
                    }
                ],
                "filter": [] # Filter ditambahkan di bawah jika ada day_of_week
            }
        },
        # Bisa ditambahkan sorting jika perlu, misal berdasarkan waktu
        # "sort": [
        #     {"timestamp": {"order": "desc"}}
        # ]
    }

    # Tambahkan filter hari jika parameter day_of_week diberikan dan valid
    if day_of_week is not None:
        # Pastikan nilai valid (Elasticsearch biasanya 0-6 untuk dayOfWeek)
        if 0 <= day_of_week <= 6:
            query["query"]["bool"]["filter"].append(
                {"term": {"dayOfWeek": day_of_week}}
            )
        else:
            # Jika tidak valid, bisa diabaikan atau beri pesan peringatan
            print(f"Peringatan: Nilai day_of_week ({day_of_week}) tidak valid. Filter hari diabaikan.")
            # Atau kembalikan pesan error: return "Error: Nilai hari tidak valid (harus 0-6)."

    # Hapus list 'filter' jika kosong (tidak ada filter hari)
    if not query["query"]["bool"]["filter"]:
        del query["query"]["bool"]["filter"]

    # Lakukan pencarian ke index penerbangan
    try:
        # print(f"Debug: Elasticsearch Flight Query: {query}") # Aktifkan untuk debugging query
        res = es.search(index="kibana_sample_data_flights", body=query) # Target index penerbangan
    except NotFoundError:
        return "Error: Index 'kibana_sample_data_flights' tidak ditemukan di Elasticsearch."
    except ConnectionError as e:
         print(f"Connection error during flight search: {e}")
         return "Maaf, terjadi masalah koneksi saat mengambil data penerbangan."
    # Tangani error spesifik jika field di multi_match tidak ada/salah mapping
    except Exception as e:
        if 'No keyword/text fields found' in str(e):
             print(f"Mapping Error in flight search: Pastikan field di '{search_fields}' ada dan bertipe text/keyword. Error: {e}")
             return "Maaf, terjadi kesalahan konfigurasi pencarian penerbangan (field tidak ditemukan)."
        print(f"Error searching flights in Elasticsearch: {e}")
        print(f"Query causing error: {query}")
        return "Maaf, terjadi kesalahan tak terduga saat mengambil data penerbangan."

    flights = res['hits']['hits']

    # Jika tidak ada hasil
    if not flights:
        day_str = f" pada hari ke-{day_of_week}" if day_of_week is not None and 0 <= day_of_week <= 6 else ""
        return f"Tidak ditemukan penerbangan yang cocok dengan '{query_string}'{day_str}."

    # --- Pemformatan Output ---
    summary_lines = []
    flight_count = 1
    criteria_str = f"yang cocok dengan '{query_string}'" + (f" pada hari ke-{day_of_week}" if day_of_week is not None and 0 <= day_of_week <= 6 else "")
    summary_lines.append(f"Berikut adalah informasi penerbangan {criteria_str}:")
    summary_lines.append("-" * 30) # Garis pemisah

    for flight in flights:
        f = flight['_source']
        # Format timestamp agar lebih mudah dibaca (opsional)
        timestamp_str = f.get('timestamp', 'N/A').replace('T', ' ') if f.get('timestamp') else 'N/A'

        # Tentukan status penerbangan
        status = "Tepat Waktu"
        if f.get('Cancelled', False):
            status = "Dibatalkan"
        elif f.get('FlightDelay', False):
            status = f"Delay ({f.get('FlightDelayType', 'Jenis tidak diketahui')})"

        details = [
            f"  Nomor: {f.get('FlightNum', 'N/A')}",
            f"  Maskapai: {f.get('Carrier', 'N/A')}",
            f"  Asal: {f.get('OriginCityName', 'N/A')} ({f.get('OriginAirportID', 'N/A')}) - {f.get('Origin', 'N/A')}",
            f"  Tujuan: {f.get('DestCityName', 'N/A')} ({f.get('DestAirportID', 'N/A')}) - {f.get('Dest', 'N/A')}",
            f"  Waktu Keberangkatan (UTC): {timestamp_str}",
            # Format durasi dan jarak agar lebih rapi
            f"  Durasi: {f.get('FlightTimeMin', 0):.1f} menit",
            f"  Jarak: {f.get('DistanceKilometers', 0):.1f} km",
            # Format harga tiket
            f"  Harga Tiket Rata-rata: ${f.get('AvgTicketPrice', 0):.2f}",
            f"  Status: {status}",
            # Tambahkan info cuaca jika relevan
            # f"  Cuaca Asal: {f.get('OriginWeather', 'N/A')}",
            # f"  Cuaca Tujuan: {f.get('DestWeather', 'N/A')}",
        ]
        # Judul untuk setiap penerbangan
        summary_lines.append(f"{flight_count}. Penerbangan {f.get('FlightNum', 'N/A')}:")
        summary_lines.extend(details)
        summary_lines.append("-" * 30) # Garis pemisah antar hasil
        flight_count += 1

    return "\n".join(summary_lines)