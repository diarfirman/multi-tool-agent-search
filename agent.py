# agent.py

import os
from dotenv import load_dotenv
#from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from elastic import get_order_summary, get_flight_info

load_dotenv()

# --- Inisialisasi LLM Menggunakan OpenAI---
# Mengambil konfigurasi dari variabel lingkungan yang sudah diatur

#llm = ChatOpenAI(
#    temperature=0,
#    model="gpt-4-0613", # Pastikan model mendukung function calling
#    openai_api_key=os.getenv("OPENAI_API_KEY")
#)

# --- Inisialisasi LLM Menggunakan Azure OpenAI ---
# Mengambil konfigurasi dari variabel lingkungan yang sudah diatur

try:
    llm = AzureChatOpenAI(
        temperature=0,
        # Menggunakan variabel lingkungan untuk konfigurasi Azure
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),       # Menggunakan kunci API Azure
        openai_api_version=os.getenv("OPENAI_API_VERSION"),   # Menggunakan versi API Azure
        # 'deployment_name' sangat penting, sesuaikan dengan nama deployment Anda di Azure
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        # Anda bisa mengatur parameter lain seperti max_tokens jika perlu
        # max_tokens=1000,
        # streaming=False # Ubah ke True jika Anda ingin respons streaming
    )
    # Opsional: Coba panggil untuk memastikan koneksi berhasil (bisa dihapus setelah testing)
    # llm.invoke("Test connection")
    print("Azure OpenAI LLM initialized successfully.")
except Exception as e:
    print(f"Error initializing Azure OpenAI LLM: {e}")
    print("Please check your Azure OpenAI environment variables in the .env file:")
    print(f"  AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"  AZURE_OPENAI_API_KEY: {'Set' if os.getenv('AZURE_OPENAI_API_KEY') else 'Not Set'}")
    print(f"  OPENAI_API_VERSION: {os.getenv('OPENAI_API_VERSION')}")
    print(f"  AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: {os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')}")
    # Hentikan eksekusi atau tangani error sesuai kebutuhan aplikasi Anda
    raise e # Atau return/exit



# --- Definisi Tools ---
# !! BUAT LIST TOOLS YANG BERISI KEDUA TOOL !!
tools = [
    # !! TOOL UNTUK DATA PEMBELIAN !!
    Tool(
        name="GetOrderSummary",
        func=get_order_summary,
        # Deskripsi diperjelas agar tidak tumpang tindih
        description=(
            "Gunakan tool ini HANYA untuk mencari informasi atau ringkasan terkait PESANAN (order), PEMBELIAN PRODUK, atau RIWAYAT BELANJA. "
            "Tool ini mencari berdasarkan kata kunci seperti nama pelanggan, nama produk, atau kategori produk. "
            "Bisa juga difilter berdasarkan HARI jika disebutkan (parameter 'day', contoh: 'Senin', 'Selasa'). "
            "Parameter utama adalah 'query_string'. "
            "JANGAN gunakan tool ini untuk informasi PENERBANGAN (flights)." # <--- Penegasan
        )
    ),
    # !! TOOL UNTUK DATA PENERBANGAN !!
    Tool(
        name="GetFlightInfo",
        func=get_flight_info, # <--- Kaitkan ke fungsi baru get_flight_info
        # Deskripsi yang jelas dan spesifik untuk penerbangan
        description=(
            "Gunakan tool ini HANYA untuk mencari informasi tentang PENERBANGAN (flights). "
            "Tool ini mencari berdasarkan kata kunci seperti kota asal (origin city), kota tujuan (destination city), "
            "nama bandara (airport name), maskapai penerbangan (carrier/airline), atau nomor penerbangan (flight number). "
            "Bisa juga difilter berdasarkan HARI DALAM SEMINGGU jika disebutkan (parameter 'day_of_week', angka 0 untuk Senin, 1 untuk Selasa, ..., 6 untuk Minggu). "
            "Parameter utama adalah 'query_string'. "
            "JANGAN gunakan tool ini untuk informasi PESANAN PRODUK atau RIWAYAT BELANJA." # <--- Penegasan
        )
    )
]

# --- Penambahan Memori Percakapan ---
MEMORY_KEY = "chat_history"
memory = ConversationBufferMemory(memory_key=MEMORY_KEY, return_messages=True)

agent_kwargs = {
    "extra_prompt_messages": [MessagesPlaceholder(variable_name=MEMORY_KEY)],
}

# --- Inisialisasi Agent Executor ---
# Agent akan otomatis menggunakan list 'tools' yang sudah diperbarui
agent_executor = initialize_agent(
    tools=tools, # <--- List ini sekarang berisi dua tool
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS, # Tipe agent yang cocok untuk memilih antar tools
    verbose=True,                     # Tetap aktifkan untuk melihat proses pemilihan tool
    agent_kwargs=agent_kwargs,
    memory=memory,
    handle_parsing_errors=True        # Penting jika output LLM kadang tidak sesuai format
)

# --- Fungsi Wrapper untuk Berinteraksi dengan Agen ---
def chat_with_agent(user_query: str) -> str:
    """
    Menjalankan query pengguna melalui agent executor yang memiliki memori
    dan dapat memilih tool yang sesuai (order summary atau flight info),
    lalu mengembalikan respons teks.
    """
    try:
        # Menggunakan .invoke
        response = agent_executor.invoke({"input": user_query})
        output = response.get("output")
        if output is None:
             print(f"Struktur respons agen tidak terduga: {response}")
             return "Maaf, terjadi format respons yang tidak terduga dari agen."
        return output

    except Exception as e:
        # Cetak error dan traceback untuk debugging yang lebih baik
        print(f"Error saat eksekusi agen: {e}")
        import traceback
        traceback.print_exc()
        # Berikan pesan error yang sedikit lebih informatif ke pengguna
        return f"Maaf, terjadi kesalahan ({type(e).__name__}) saat memproses permintaan Anda. Silakan coba lagi atau hubungi administrator jika masalah berlanjut."

# Tidak perlu perubahan pada sisa kode agent.py