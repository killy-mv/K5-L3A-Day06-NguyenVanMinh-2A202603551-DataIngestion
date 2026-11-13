# Starter · PostgreSQL + pgvector

Bộ khởi động **tùy chọn** cho lab cá nhân. Docker Compose tạo PostgreSQL + pgvector local; các file trong `src/` là **khung pseudocode có TODO**, chưa đọc tài liệu, tạo embedding, lưu vector hay chạy benchmark. Bạn cần tự hiện thực. Vẫn có thể chọn Qdrant, Chroma hoặc vector store tương đương theo [GUIDE.md](../GUIDE.md).

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # psycopg, pypdf và python-dotenv
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc dữ liệu mẫu
│   ├── ingestion.py       # TODO: đọc / chuẩn hóa tài liệu
│   ├── chunking.py        # TODO: chia chunk
│   ├── embeddings.py      # TODO: chọn model API hoặc local
│   ├── store.py           # TODO: lưu vector, metadata và filter
│   ├── evaluation.py      # TODO: chấm truy xuất, lưu trace
│   └── run.py             # TODO: kết nối các bước thành pipeline
├── data/                  # bạn tự chuẩn bị corpus được phép sử dụng
└── results/               # lưu kết quả của bạn
```

## 1. Cài và kiểm tra database

Cần Docker Desktop hoặc Docker Engine + Compose, Python **3.11–3.14**, và mạng để tải image/dependencies lần đầu. Các lệnh sau chạy từ thư mục `starter/`:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt `.venv`: macOS/Linux dùng `source .venv/bin/activate`; Windows PowerShell dùng `.venv\Scripts\Activate.ps1`. Sau đó:

```bash
python -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`. `init.sql` chỉ chạy khi volume mới được tạo; nếu database sẵn có chưa bật extension, xem log Docker và kiểm tra cấu hình thay vì xóa volume chứa dữ liệu.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Chọn embedding model

Điền key tương ứng trong `.env` nếu dùng OpenRouter, OpenAI hoặc Gemini; **không commit `.env`**. Model local không cần API key. `requirements.txt` chỉ có dependencies cơ bản: tự cài SDK hoặc thư viện local phù hợp với model bạn chọn và ghi lại version/lệnh cài trong báo cáo. Ghi tên model và số chiều; dùng cùng model cho toàn bộ chiến lược và vector query tương thích vector document.

## 3. Hoàn thiện pipeline

1. Đặt corpus vào `data/` hoặc cung cấp manifest/hướng dẫn truy cập. Đọc [GUIDE.md](../GUIDE.md) về **30 trang nội dung**, quyền dữ liệu và metadata.
2. Hoàn thiện từng hàm TODO trong `src/`. Lưu ID tài liệu, nguồn, trang/vị trí và ít nhất một trường filter có ích.
3. Xây ít nhất ba cấu hình; ví dụ A fixed-size, B theo đoạn, C như B nhưng có filter. Cần cùng corpus, model và benchmark; nạp lại không nhân đôi và xử lý chunk cũ khi dữ liệu đổi.
4. Tự viết ít nhất 20 câu hỏi kèm evidence, tách dev/test trước khi thử theo [BENCHMARK.md](../BENCHMARK.md). Lưu trace top-3 và báo cáo đủ năm tiêu chí.
5. Sau khi hoàn thiện, chạy `python -m src.run` từ thư mục `starter/`. Trước khi làm TODO, lệnh này **chủ động báo `NotImplementedError`**.

Lưu code, cấu hình, kết quả và lệnh chạy để người chấm tái lập; không commit key, dữ liệu mật hoặc dữ liệu không có quyền chia sẻ.

## CP3: ingestion + two chunking methods (implemented)

With the CP1 PDF and manifest at repository root, run from `starter/`:

```bash
.venv/Scripts/python.exe -m src.cp3
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

This stage validates the corpus SHA256; ingests 35 PDF pages; builds fixed-size strategy A (500 chars, 50 overlap) and paragraph-aware strategy B (max 650 chars); preserves `document_id`, `source`, physical PDF `page`, and filterable `chapter` metadata. It writes real JSONL chunk exports, audit diagnostics, and statistics to `starter/results/`. Strategy C will reuse B chunks at retrieval time with metadata filtering. See `../docs/CP3_INGESTION.md` and `results/cp3_statistics.json`.

**Important:** The provided `python -m src.run` full-pipeline entry remains TODO until CP4/CP5. Running CP3 does not create embeddings or a vector index.

## CP4: real embeddings and pgvector retrieval (implemented)

```bash
cd starter
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m src.cp3
.venv/Scripts/python.exe -m src.cp4
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

`src.cp4` indexes 170 fixed chunks as A and 160 paragraph chunks as B in PostgreSQL + pgvector. C reuses B's vectors with optional `chapter` filtering. Local CPU `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) is used for both documents and queries; no embedding API key needed. Run artifacts and smoke top-3 traces are saved in `results/cp4_*`. See `../docs/CP4_VECTOR_STORAGE.md`. Benchmark dev/test evaluation and manual audit are intentionally deferred to CP5.

## CP5: frozen benchmark (completed)

Run from `starter/`, only on a clean CP5 results folder, in this strict order:

```bash
.venv/Scripts/python.exe -m src.run --stage dev
.venv/Scripts/python.exe -m src.cp5_audit
.venv/Scripts/python.exe -m src.run --stage freeze
.venv/Scripts/python.exe -m src.run --stage test
.venv/Scripts/python.exe -m src.cp5_finalize
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

The scripts refuse accidental overwrites of frozen benchmark runs. Completed files are under `results/cp5_*`, including full top-3 texts, scores, auditable source page metadata, per-question strict Hit@1 / Evidence Hit@3, and AI-assisted qualitative audits. Strategy B was locked on Dev before any Test queries. Do not describe AI-assisted coherence or grounding assessments as independent human ratings. See `../docs/CP5_EVALUATION.md` and `../artifacts/experiment_log.csv` for actual outcomes.
