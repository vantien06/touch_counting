# Touch Counting

He thong computer vision dung Ultralytics YOLO de tracking nguoi trong video/camera, kiem tra tam bounding box nam trong zone va ghi nhan visit khi nguoi o trong zone du thoi gian dwell.

## 1. Cau truc project

- `main.py`: doc video/RTSP, YOLO tracking, dwell time, ID handoff, preview, CSV va MP4.
- `draw_zones.py`: ve cac zone hinh chu nhat tren frame dau tien.
- `config.yaml`: model, tracker, dwell time va danh sach zone.
- `requirements.txt`: cac package Python can thiet.

## 3. Mo bang mot lenh

Chay lenh sau de mo giao dien dieu khien:

```powershell
python gui.py
```

### Chay tren may khac khong can quyen admin

Giai nen goi ZIP vao mot thu muc ma nguoi dung co quyen ghi. May dich can co Python va pip.

1. Chay `INSTALL_REQUIREMENTS.bat` de cai cac thu vien vao tai khoan nguoi dung hien tai.
2. Chay `RUN_GUI.bat` de mo giao dien.

Khong can cai dat vao `Program Files` va khong can quyen administrator. Khong di chuyen rieng cac file `.pt`, `config.yaml`, `camera_configs` hoac `logo` ra khoi thu muc project.

Trong giao dien:

- Chon camera trong danh sach; bam `Lam moi` neu vua cam them camera.
- Dat ten de nhan biet cho camera trong o `Camera name` (vi du `Nescafe`, `Milo`) va bam `Save name`; ten nay duoc luu lai theo dung thiet bi.
- Chuong trinh se yeu cau camera mo o muc toi da `3840x2160`; danh sach hien do phan giai thuc te camera tra ve.
- Bam `Ve / sua zone` de mo cua so ve zone cho camera dang chon.
- Chinh cac tuy chon tracking truc tiep trong giao dien, sau do bam `Start tracking` cho camera dang chon hoac `Start all cameras` de chay dong thoi tat ca camera.
- Moi camera tu dong dung mot file config rieng trong `camera_configs/`, duoc gan theo ID thiet bi thay vi chi theo index. Neu Windows doi camera 0 thanh camera 1, zone van di theo dung camera.
- Nhieu camera co the ghi chung vao mot file CSV; moi dong co ten camera va do phan giai.
- Bam `Dung` de ket thuc tracking.

## 4. Cai dat moi truong

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

## 5. Ve zone

Chay:

```powershell
python draw_zones.py --video demo.mp4 --config config.yaml
```

Neu dung camera laptop, thuong dung camera index `0`:

```powershell
python draw_zones.py --video 0 --config config.yaml
```

Neu co nhieu camera, liet ke camera dang ket noi:

```powershell
python draw_zones.py --list-cameras
```

Sau do chon camera bang index, vi du camera `1`:

```powershell
python draw_zones.py --camera 1 --config config.yaml
```

Dieu khien cua so OpenCV:

- Keo chuot trai de ve mot hinh chu nhat.
- `u`: xoa zone vua ve.
- `s`: luu zone vao `config.yaml` va thoat.
- `q` hoac `Esc`: thoat khong luu.

Zone duoc luu duoi dang danh sach `points`, nen sau nay co the mo rong thanh polygon.

## 6. Cau hinh

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

## 7. Chay video va CSV

Chay toan bo video, ghi visit vao `events.csv`:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv
```

Test gioi han 100 frame:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --max-frames 100
```

`--max-frames 0` hoac khong truyen tuy chon nay se xu ly den het video.

De dung camera laptop, truyen camera index thay cho ten video. Camera dau tien thuong la `0`, camera tiep theo la `1`:

```powershell
python main.py --video 0 --config config.yaml --output events.csv --preview
```

Voi nhieu camera, liet ke truoc:

```powershell
python main.py --list-cameras
```

Ket qua se hien index va kich thuoc, vi du `Camera 1: 1920x1080`. Dung index do de chon camera:

```powershell
python main.py --camera 1 --config config.yaml --output events.csv --preview
```

Camera se chay lien tuc cho den khi nhan `q`/`Esc` trong cua so preview. Co the dung `--max-frames` de gioi han so frame khi test.

Trong luc chay, chuong trinh in so frame da xu ly, FPS xu ly va ETA.

## 8. Preview

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

## 9. Xuat video da xu ly

Phai truyen tuy chon `--save-video`; neu khong, chuong trinh chi ghi CSV va khong tao MP4:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --save-video processed.mp4
```

Ket hop preview va xuat video:

```powershell
python main.py --video demo.mp4 --config config.yaml --output events.csv --preview --save-video processed.mp4
```

Video output giu kich thuoc va FPS cua video goc. Codec `mp4v` duoc dung de tuong thich voi OpenCV tren Windows.

## 10. Camera RTSP

Thay gia tri `--video` bang URL RTSP:

```powershell
python main.py --video "rtsp://user:password@192.168.1.10:554/stream" --config config.yaml --output events.csv --preview --save-video processed.mp4
```

Neu URL co ky tu dac biet, dat toan bo URL trong dau ngoac kep.

## 11. CSV output

Moi visit hoan chinh co cac cot ro rang:

- `camera`: camera da ghi nhan visit, vi du `Camera 0`.
- `camera_resolution`: do phan giai frame cua camera, vi du `3840x2160`.
- `recorded_at_utc`: thoi diem ghi nhan theo UTC.
- `person_id`: ID tam thoi cua nguoi do tracker cap.
- `zone`: ten zone, vi du `Region A`.
- `entry_frame`
- `exit_frame`
- `entry_time_seconds`: thoi gian tu luc bat dau tracking den khi vao zone.
- `exit_time_seconds`: thoi gian tu luc bat dau tracking den khi roi zone.
- `time_in_zone_seconds`: tong thoi gian o trong zone.

Nguoi roi zone truoc khi du `dwell_seconds` se khong duoc ghi log. Neu dang active khi video ket thuc, visit se duoc dong tai frame cuoi.

## 12. Xu ly mat ID

Trang thai visit khong phu thuoc hoan toan vao ID hien tai. Neu ID bi mat tam thoi, chuong trinh giu visit trong `id_switch_grace_seconds`. Khi ID moi xuat hien gan tam cu trong `id_switch_distance_pixels`, visit se duoc chuyen sang ID moi va khong reset dwell timer.

## 13. Xu ly loi thuong gap

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
