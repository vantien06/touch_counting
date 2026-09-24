# Touch Counting

He thong computer vision dung Ultralytics YOLO de tracking nguoi trong video/camera, kiem tra tam bounding box nam trong zone va ghi nhan visit khi nguoi o trong zone du thoi gian dwell.

## 1. Cau truc project

- `main.py`: doc video/RTSP, YOLO tracking, dwell time, ID handoff, preview, CSV va MP4.
- `draw_zones.py`: ve cac zone hinh chu nhat tren frame dau tien.
- `config.yaml`: model, tracker, dwell time va danh sach zone.
- `requirements.txt`: cac package Python can thiet.

## 2. Cai dat moi truong

Mo PowerShell tai thu muc project:

```powershell
conda activate touchCounting
pip install -r requirements.txt
```

Neu chua co environment:

```powershell
conda create -n touchCounting python=3.11 -y
conda activate touchCounting
pip install -r requirements.txt
```

Model YOLO se duoc Ultralytics tu dong tai ve khi chay lan dau. Co the chon `yolo26n.pt`, `yolo26s.pt` hoac `yolo26m.pt` trong `config.yaml`.

## 3. Ve zone

Chay:

```powershell
python draw_zones.py --video demo.mp4 --config config.yaml
```

Dieu khien cua so OpenCV:

- Keo chuot trai de ve mot hinh chu nhat.
- `u`: xoa zone vua ve.
- `s`: luu zone vao `config.yaml` va thoat.
- `q` hoac `Esc`: thoat khong luu.

Zone duoc luu duoi dang danh sach `points`, nen sau nay co the mo rong thanh polygon.

## 4. Cau hinh

Vi du:

```yaml
model: yolo26s.pt
confidence: 0.25
imgsz: native
tracker: bytetrack.yaml
dwell_seconds: 5.0
id_switch_grace_seconds: 1.0
id_switch_distance_pixels: 120.0
regions:
  - name: region_A
    points:
      - [855, 254]
      - [996, 254]
      - [996, 421]
      - [855, 421]
```

Y nghia cac tuy chon:

- `model`: `yolo26n.pt`, `yolo26s.pt` hoac `yolo26m.pt`.
- `confidence`: nguong confidence cua YOLO.
- `imgsz`: `native`, `max` hoac `maximum` dung canh lon nhat cua frame. Cung co the dat so cu the nhu `1280` hoac `640`.
- `tracker`: thuong dung `bytetrack.yaml`; co the doi sang tracker Ultralytics khac.
- `dwell_seconds`: so giay tam bounding box phai nam lien tuc trong zone de bat dau tinh visit.
- `id_switch_grace_seconds`: thoi gian cho phep mat ID tam thoi.
- `id_switch_distance_pixels`: khoang cach toi da de gan ID moi vao visit cu.

Voi video `1920x1080`, `imgsz: native` tuong duong `imgsz=1920`, cho ket qua chi tiet hon nhung cham va ton VRAM/RAM hon. Khi test tren CPU, nen dung `1280` hoac `640`.

## 5. Chay video va CSV

Chay toan bo video, ghi visit vao `events.csv`:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv
```

Test gioi han 100 frame:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --max-frames 100
```

`--max-frames 0` hoac khong truyen tuy chon nay se xu ly den het video.

Trong luc chay, chuong trinh in so frame da xu ly, FPS xu ly va ETA.

## 6. Preview

Mo cua so preview:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --preview
```

Nhan `q` hoac `Esc` trong cua so preview de dung.

Mau hien thi:

- Cam: nguoi co `track_id`.
- Do: YOLO detect duoc nguoi nhung chua co `track_id`.
- Hong: tam bounding box dung de kiem tra zone.
- Vang: zone dang cho du dwell time.
- Xanh la: zone dang co visit duoc tinh.
- Do tim: zone khong co nguoi hop le.

Tam bounding box duoc tinh bang:

```text
center_x = (x1 + x2) / 2
center_y = (y1 + y2) / 2
```

Khong dung diem day bounding box, phu hop voi camera goc xeo.

## 7. Xuat video da xu ly

Phai truyen tuy chon `--save-video`; neu khong, chuong trinh chi ghi CSV va khong tao MP4:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --save-video processed.mp4
```

Ket hop preview va xuat video:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --preview --save-video processed.mp4
```

Video output giu kich thuoc va FPS cua video goc. Codec `mp4v` duoc dung de tuong thich voi OpenCV tren Windows.

## 8. Camera RTSP

Thay gia tri `--video` bang URL RTSP:

```powershell
python main.py --video "rtsp://user:password@192.168.1.10:554/stream" --config config.yaml --output events.csv --preview --save-video processed.mp4
```

Neu URL co ky tu dac biet, dat toan bo URL trong dau ngoac kep.

## 9. CSV output

Moi visit hoan chinh co cac cot:

- `logged_at_utc`
- `track_id`
- `region`
- `entry_frame`
- `exit_frame`
- `entry_seconds`
- `exit_seconds`
- `duration_seconds`

Nguoi roi zone truoc khi du `dwell_seconds` se khong duoc ghi log. Neu dang active khi video ket thuc, visit se duoc dong tai frame cuoi.

## 10. Xu ly mat ID

Trang thai visit khong phu thuoc hoan toan vao ID hien tai. Neu ID bi mat tam thoi, chuong trinh giu visit trong `id_switch_grace_seconds`. Khi ID moi xuat hien gan tam cu trong `id_switch_distance_pixels`, visit se duoc chuyen sang ID moi va khong reset dwell timer.

## 11. Xu ly loi thuong gap

### Chay qua cham

Dat trong `config.yaml`:

```yaml
imgsz: 1280
```

Hoac:

```yaml
imgsz: 640
```

Model `yolo26n.pt` nhanh hon `yolo26s.pt` va `yolo26m.pt`.

### Nguoi dung yen bi mat detection

- Giam `confidence`, vi du `0.20`.
- Tang `imgsz` neu GPU/RAM cho phep.
- Phan biet detection bi mat voi tracking ID bi mat.
- Dieu chinh `id_switch_grace_seconds` va `id_switch_distance_pixels`.

### Khong thay MP4

Kiem tra lenh co `--save-video processed.mp4` hay khong. Chi `--preview` khong tu dong tao video.

### Khong thay preview

Kiem tra lenh co `--preview` va dang chay trong session Windows co giao dien. Cua so se hien thi thong bao `Loading model...` truoc khi YOLO bat dau inference.

### Kiem tra code

```powershell
python -m py_compile main.py draw_zones.py
```

Khi test xuat video, co the doc lai file bang OpenCV:

```powershell
python -c "import cv2; cap=cv2.VideoCapture('processed.mp4'); print(cap.isOpened(), cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT), cap.get(cv2.CAP_PROP_FPS)); cap.release()"
```
