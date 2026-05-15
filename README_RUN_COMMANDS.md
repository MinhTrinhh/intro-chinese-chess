# Hướng dẫn chạy các lệnh Self-Play Training

## Chuẩn bị môi trường

```bash
# Kích hoạt virtual environment
.\.venv\Scripts\Activate.ps1

# Cài đặt dependencies (nếu chưa có)
pip install -r requirements.txt
```

---

## 1. Sinh dữ liệu Self-Play (Mass Selfplay Generation)

### Cấu hình 1: 3v2 và 2v3

```bash
python -m src.ml.mass_selfplay_gen \
  --games 100 \
  --workers 8 \
  --output-dir data \
  --combined-output data/combined_dataset_config1.pkl
```

Cài đặt:
- **3v2**: Red depth=3, Black depth=2
- **2v3**: Red depth=2, Black depth=3
- **Không có 3v3**

### Cấu hình 2: 3v2, 2v3 và 3v3

```bash
python -m src.ml.mass_selfplay_gen \
  --games 100 \
  --workers 8 \
  --output-dir data \
  --combined-output data/combined_dataset_config2.pkl
```

Cài đặt:
- **3v2**: Red depth=3, Black depth=2
- **2v3**: Red depth=2, Black depth=3
- **3v3**: Red depth=3, Black depth=3 (sử dụng DEFAULT_CONFIGS)

**Lưu ý**: Để tùy chỉnh số trò chơi, thay đổi `--games` (mặc định: 100)

---

## 2. Huấn luyện mô hình trên GPU

### Chạy training đơn giản (từ dữ liệu đã sinh)

```bash
python train_model.py \
  --data-path data/combined_dataset_config2.pkl \
  --epochs 50 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --device cuda \
  --output-dir models
```

### Chạy với validation split

```bash
python train_model.py \
  --data-path data/combined_dataset_config2.pkl \
  --epochs 50 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --validation-split 0.2 \
  --device cuda \
  --output-dir models
```

**Tham số**:
- `--data-path`: Đường dẫn tới file pickle chứa training data
- `--epochs`: Số epoch training (mặc định: 50)
- `--batch-size`: Kích thước batch (mặc định: 64)
- `--learning-rate`: Learning rate cho optimizer (mặc định: 0.001)
- `--device`: Thiết bị (cuda/cpu, mặc định: cuda)
- `--output-dir`: Thư mục lưu checkpoint

---

## 3. Đánh giá mô hình sau khi train

### Chạy evaluation cơ bản (RED có model, BLACK là pure search)

```bash
python -m src.ml.selfplay_model_eval \
  --games 10 \
  --red-depth 2 \
  --black-depth 3 \
  --model models/trained_model.pth \
  --device cuda
```

### Chạy với debug logging (xem chi tiết từng nước đi)

```bash
python -m src.ml.selfplay_model_eval \
  --games 5 \
  --red-depth 2 \
  --black-depth 3 \
  --model models/trained_model.pth \
  --device cuda \
  --debug
```

**Tham số**:
- `--games`: Số trò chơi để đánh giá
- `--red-depth`: Độ sâu tìm kiếm của Red
- `--black-depth`: Độ sâu tìm kiếm của Black
- `--model`: Đường dẫn tới model checkpoint (nếu không cung cấp, sẽ chạy pure AlphaBeta)
- `--device`: Thiết bị (cuda/cpu)
- `--debug`: Bật logging HTML chi tiết

**Output**: Thống kê kết quả gồm Red wins, Black wins, Draws

---

## Quy trình hoàn chỉnh từ đầu đến cuối

```bash
# 1. Sinh dữ liệu training (Cấu hình 2)
python -m src.ml.mass_selfplay_gen --games 200 --workers 8 --combined-output data/combined_dataset_config2.pkl

# 2. Train mô hình trên GPU
python train_model.py \
  --data-path data/combined_dataset_config2.pkl \
  --epochs 50 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --device cuda \
  --output-dir models

# 3. Đánh giá mô hình vừa train
python -m src.ml.selfplay_model_eval \
  --games 20 \
  --red-depth 2 \
  --black-depth 3 \
  --model models/trained_model.pth \
  --device cuda
```

---

## Ghi chú

- **Thư mục logs**: Các file HTML debug được lưu tại `logs/selfplay_debug/`
- **Thư mục data**: Dữ liệu pickle được lưu tại `data/`
- **Thư mục models**: Checkpoint mô hình được lưu tại `models/`
- **GPU**: Đảm bảo CUDA available nếu dùng `--device cuda`
- **Workers**: Tăng `--workers` để sinh dữ liệu nhanh hơn (mặc định: 8)
