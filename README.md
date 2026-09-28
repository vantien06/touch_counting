# Touch Counting

Ứng dụng Windows dùng Python, OpenCV và Ultralytics YOLO để tracking người, tính tâm bounding box và ghi visit khi người ở trong zone đủ thời gian dwell.

## Cài đặt và chạy GUI

```powershell
conda create -n touchCounting python=3.12 -y
conda activate touchCounting
pip install -r requirements.txt
python gui.py
```

Để chạy nhanh trên Windows, double-click `run_touch_counting.bat`. Khi copy project sang máy khác, chạy `create_desktop_shortcut.bat` một lần trên máy đó để tạo shortcut mới ngoài Desktop; không copy file `.lnk` từ máy cũ vì shortcut Windows chứa đường dẫn tuyệt đối. CSV mặc định được ghi vào Desktop của máy đang chạy.

Trong GUI, chọn camera, bấm `Refresh` sau khi cắm/tháo thiết bị, chọn config và CSV, bấm `Vẽ / sửa zone`, kéo chuột để tạo vùng rồi bấm `s` để lưu. Sau đó bấm `Bắt đầu tracking`. Phím `q` hoặc `Esc` trong preview dừng tracking. Mặc định model sẽ được Ultralytics tải khi chạy lần đầu; có thể đổi tên model trong `config.yaml`.

## CLI tương thích

```powershell
python main.py --list-cameras
python main.py --camera 0 --config config.yaml --output events.csv --preview
python draw_zones.py --camera 0 --config config.yaml
python main.py --video sample.mp4 --max-frames 300 --save-video processed.mp4
python main.py --video rtsp://user:password@host/stream --preview
```

`--camera` và `--video` loại trừ nhau. Khi không truyền nguồn, CLI dùng Camera 0. Camera được dò từ index 0 đến 9 và thử các mode từ 4K xuống; độ phân giải hiển thị là kích thước frame thực tế mà driver trả về. Nếu thấp, hãy đóng ứng dụng khác đang dùng camera và kiểm tra giới hạn driver.

## CSV và xử lý lỗi

`events.csv` dùng UTF-8 và có tên camera custom đã lưu trong GUI, cùng các cột `camera`, `camera_resolution`, `recorded_at_utc`, `zone`, `entry_frame`, `exit_frame`, `entry_time_seconds`, `exit_time_seconds`, `time_in_zone_seconds`. `person_id` không được ghi vì ID tracking có thể thay đổi giữa các frame. Visit chưa đạt dwell không được ghi; visit hợp lệ được ghi ngay khi đóng hoặc khi chương trình dừng.

Nếu không thấy camera, bấm `Refresh`, thử đổi cổng USB và đóng Zoom/Teams/Camera. Nếu preview không hiện, kiểm tra OpenCV GUI và chạy lại với `--preview`. Model lớn sẽ chậm hơn; dùng model nhỏ hoặc giảm `imgsz` trong YAML. Lỗi import dependency được xử lý bằng `pip install -r requirements.txt` trong đúng environment `touchCounting`.