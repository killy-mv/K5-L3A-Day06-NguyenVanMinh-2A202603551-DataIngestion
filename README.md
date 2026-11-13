# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.

---

## Bai lam ca nhan - ket qua thuc te (CP1-CP6)

**Hoc vien:** Nguyen Van Minh - 2A202603551, L3A. **Trang thai:** da chay pipeline, benchmark va luu toan bo minh chung; cho xac nhan nhan danh gia thu cong va nop link cuoi cung. Xem [bao cao ca nhan](report/individual/2A202603551_NguyenVanMinh.md), [CP6 final review](docs/CP6_FINAL_REVIEW.md).

### Yeu cau may de tai lap

Windows + Docker Desktop (Linux containers), Python 3.14, internet de cai dependency / model neu chua duoc cache. Model la `sentence-transformers/all-MiniLM-L6-v2`, 384 chieu, CPU. Docker chay PostgreSQL 16 va pgvector; port host `127.0.0.1:55433`. Luu y trong Git Bash o may da test, `python` co the tro ve Microsoft Store alias; dung `py -3.14` de tao env va `.venv/Scripts/python.exe` sau do.

```bash
# Tu root repository
cd starter
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env
# .env chi su dung ket noi local va khong commit len git
docker compose -p day6_student_starter up -d --wait
.venv/Scripts/python.exe scripts/check_setup.py

# CP3 - doc, chuan hoa va chia 35 trang tai lieu
.venv/Scripts/python.exe -m src.cp3
# CP4 - embed va luu vector vao pgvector, smoke search
.venv/Scripts/python.exe -m src.cp4
# Unit + integration tests
.venv/Scripts/python.exe -m unittest discover -s tests -v
cd ..

# Bao dam gold benchmark khong bi thay doi
starter/.venv/Scripts/python.exe scripts/validate_benchmark.py
# Kiem toan cuoi KHONG chay lai Test
starter/.venv/Scripts/python.exe scripts/final_audit.py
```

**CP5 da chay, khong can chay lai de nop.** Neu can kiem chung thuc nghiem tu mot ban sao moi, xem [quy trinh Dev/freeze/Test](docs/CP5_EVALUATION.md). Scripts CP5 tu choi ghi de trace va quyet dinh khoa; sao luu file output cu truoc khi thuc hien mot run doc lap moi. Khong thay doi tap Test cu de toi uu.

### Ket qua tong hop

| Cau hinh | Chunks vat ly | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|---:|
| A - Fixed (500, overlap 50) | 170 | 4/15 | 9/15 | 0/5 | 2/5 |
| B - Paragraph (max 650) | 160 | 9/15 | 12/15 | 2/5 | 4/5 |
| C - B + chapter filter | 160 (reuse B) | 9/15 | 12/15 | 2/5 | 4/5 |

**B duoc chon tren Dev truoc khi xem Test.** Evidence Hit@3 la ty le lay du *nguyen van gold evidence trong cung mot chunk* cua dung source/page; khong do accuracy cau tra loi chatbot. Danh gia coherence/grounding trong audit la AI-assisted, co chunk IDs va ly do; can nguoi hoc xac nhan neu bat buoc danh gia thu cong doc lap.

### File da nop kem trong repository

- `data/source/thinkpython2.pdf` + `data/manifest.json`: 35 trang noi dung, nguon/giay phep CC BY-NC 3.0, SHA256, metadata.
- `benchmark/questions.json` + `split_lock.json`: 20 cau, 15 Dev / 5 Test, gold evidence.
- `starter/src/` + `starter/tests/`: ingest, chunking, embedding, pgvector, retrieval, evaluation, audit va unit tests.
- `starter/results/cp3_*`, `cp4_*`, `cp5_*`, `cp6_*`: log, day du top-3 text/score/metadata, chi so, nhan audit va bang chung runtime.
- `artifacts/experiment_log.csv`, `docs/CP*_*.md`, `report/individual/2A202603551_NguyenVanMinh.md`, `SUBMISSION.md`.

**Nguon sach:** Allen B. Downey, *Think Python 2nd Edition*, https://greenteapress.com/thinkpython2/thinkpython2.pdf (CC BY-NC 3.0, su dung giao duc phi thuong mai va giu nguon). Khong su dung API embedding tinh phi; CPU, dien va storage van la tai nguyen that.
