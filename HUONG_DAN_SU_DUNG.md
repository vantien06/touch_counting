# Hướng dẫn sử dụng Touch Counting

Tài liệu này dành cho người sử dụng gói portable trên Windows. Người dùng không cần cài Python, Conda hoặc các thư viện bổ sung.

## 1. Nhận và giải nén file ZIP

1. Nhận file `touch_counting_portable.zip`.
2. Nhấn chuột phải vào file ZIP và chọn **Extract All...** (hoặc **Giải nén tất cả...**).
3. Chọn một thư mục dễ tìm, ví dụ `Desktop\touch_counting_portable`.
4. Nhấn **Extract**.

Không chạy chương trình trực tiếp bên trong file ZIP. Hãy giải nén toàn bộ nội dung trước khi sử dụng.

Sau khi giải nén, thư mục cần có các file chính sau (chỉ để tham khảo, không cần quan tâm):

- `run_portable.bat`: file khởi động chương trình.
- `gui.py`, `main.py`: các thành phần chạy chương trình.
- `environment.zip`: môi trường Python đi kèm.
- Các file model `.pt`, `config.yaml` và thư mục `camera_configs`.

## 2. Khởi động chương trình

1. Kết nối camera USB hoặc camera cần sử dụng với máy tính.
2. Mở thư mục đã giải nén.
3. Nhấn đúp vào file **`run_portable.bat`**.
4. Cửa sổ **Touch Counting** sẽ mở sau khi môi trường được chuẩn bị xong. Ở lần chạy đầu tiên có thể mất vài phút

Từ lần chạy sau, chỉ cần nhấn đúp `run_portable.bat` để mở chương trình. Không xóa thư mục `environment` sau lần chạy đầu, vì đây là môi trường chạy của ứng dụng.

## 3. Chọn camera

Trong cửa sổ chương trình:

1. Xem danh sách tại mục **Camera**.
2. Chọn camera cần theo dõi.
3. Xem hình ảnh tại **Camera preview** để kiểm tra đúng camera.
4. Nếu vừa cắm hoặc tháo camera, nhấn **Refresh**.
5. Có thể nhập tên dễ nhận biết tại **Camera name**, sau đó nhấn **Save name**.

Nếu có nhiều camera, mỗi camera có thể được cấu hình zone và tên riêng. Nút **Start tracking** chỉ chạy camera đang chọn; nút **Start all cameras** chạy tất cả camera đang được nhận diện.

## 4. Tạo hoặc chỉnh sửa vùng theo dõi

Zone là vùng trên hình ảnh mà chương trình dùng để tính thời gian một người ở bên trong.

1. Chọn camera cần cấu hình.
2. Nhấn **Draw / edit zones**.
3. Trong cửa sổ hình ảnh, kéo chuột để vẽ từng vùng cần theo dõi.
4. Nhấn phím `s` trên bàn phím để lưu zone.
5. Đóng cửa sổ vẽ zone hoặc quay lại cửa sổ chính.
6. Nhấn **Reload zones** trong phần **Zone settings**.

Với mỗi zone, nhập:

- **Name**: tên zone, ví dụ `Cửa vào` hoặc `Kệ A`.
- **Offset (touches/min)**: số touch quy đổi cho mỗi phút ở trong zone.

Nếu cần sửa zone, thực hiện lại từ bước 2. Zone mới sẽ chỉ xuất hiện trong bảng sau khi nhấn **Reload zones**.

## 5. Điều chỉnh thông số (không bắt buộc)

Các thông số thường dùng trong **Tracking settings**:

- **Model**: `Nano` chạy nhanh nhất, `Small` cân bằng, `Medium` chính xác hơn nhưng chậm hơn.
- **Confidence**: ngưỡng nhận diện người. Giá trị thấp nhận diện được nhiều trường hợp hơn nhưng có thể tăng nhận diện nhầm. (từ 0 đến 1)
- **Resolution**: độ phân giải đưa vào model. Giá trị thấp chạy nhanh hơn; giá trị cao có thể nhận diện người nhỏ tốt hơn.
- **Zone time (sec)**: số giây một người phải ở trong zone trước khi visit được ghi nhận.
- **Lost ID grace (sec)**: thời gian cho phép mất nhận diện người tạm thời mà không kết thúc visit.
- **ID recovery (px)**: khoảng cách tối đa để nối lại một người sau khi ID tracking thay đổi.

Nếu không có yêu cầu đặc biệt, nên giữ giá trị mặc định.

## 6. Chọn nơi lưu kết quả

Mục **Output CSV** là đường dẫn file kết quả.

- Mặc định: `Desktop\events.csv` của tài khoản Windows đang chạy chương trình.
- Muốn đổi nơi lưu, nhấn **Browse**, chọn thư mục và đặt tên file `.csv`.
- Nếu chạy nhiều camera, có thể dùng cùng một file CSV để ghi chung kết quả.

## 7. Bắt đầu và kết thúc theo dõi

1. Kiểm tra camera, zone, tên zone và đường dẫn **Output CSV**.
2. Tích **Open preview window** nếu muốn xem hình ảnh đang được xử lý.
3. Nhấn **Start tracking** để bắt đầu camera đang chọn, hoặc **Start all cameras** để chạy tất cả camera.
4. Khi muốn kết thúc, nhấn **Stop** trong cửa sổ chính.

Khi đang chạy, cửa sổ preview hiển thị zone, người được nhận diện và tổng touch tạm tính của từng zone. Nếu cửa sổ preview đang được chọn, có thể nhấn `q` hoặc `Esc` để dừng theo dõi.

Visit hợp lệ được ghi vào CSV khi người đó rời zone hoặc khi chương trình dừng. Visit chưa đủ **Zone time (sec)** sẽ không được ghi.

## 8. Xem kết quả

Mở file `events.csv` bằng Microsoft Excel, LibreOffice Calc hoặc ứng dụng bảng tính tương tự.

Mỗi dòng là một visit hợp lệ, gồm các thông tin chính:

- Camera và độ phân giải camera.
- Thời điểm vào/ra zone.
- Tên zone.
- Thời gian ở trong zone.
- `touch_count`: số touch được tính cho visit đó.

Công thức tính:

```text
touch_count = thời gian ở trong zone (phút) x Offset (touches/min)
```

Ví dụ: một người ở trong zone 2 phút và zone có offset 30 touches/min thì kết quả là 60 touch. Số liệu trong CSV có thể có phần thập phân.

## 9. Cách đóng chương trình

Sau khi nhấn **Stop** và trạng thái chuyển về **Tracking finished** hoặc **Tracking stopped**, có thể đóng cửa sổ Touch Counting. Không xóa hoặc di chuyển file CSV trong lúc chương trình đang chạy.

## 10. Xử lý sự cố thường gặp

### Không thấy camera

- Kiểm tra camera đã được kết nối chưa.
- Đóng các ứng dụng đang sử dụng camera như Teams, Zoom, Camera hoặc trình duyệt.
- Nhấn **Refresh**.
- Thử đổi cổng USB rồi mở lại chương trình.

### Chương trình không mở khi nhấn `run_portable.bat`

- Đảm bảo ZIP đã được giải nén hoàn toàn.
- Không đổi tên hoặc xóa `environment.zip` trước lần chạy đầu.
- Đảm bảo thư mục đã giải nén có `run_portable.bat` và `environment.zip` cùng cấp.
- Nếu Windows hiển thị cảnh báo bảo mật, chọn **More info** rồi **Run anyway** khi phù hợp với chính sách của máy.

### Không có dữ liệu trong CSV

- Kiểm tra đã chọn đúng camera và đúng zone.
- Đảm bảo người ở trong zone lâu hơn **Zone time (sec)**.
- Kiểm tra đường dẫn trong **Output CSV** và quyền ghi vào thư mục đó.
- Nhấn **Stop** để đóng các visit đang còn mở và ghi chúng vào file.

### Chương trình chạy chậm

- Chọn model nhỏ hơn, ví dụ `Nano`.
- Giảm **Resolution**.
- Đóng các chương trình nặng khác.
- Nếu đang dùng nhiều camera, thử chạy từng camera bằng **Start tracking**.

### Lỗi hoặc cửa sổ tự đóng

Giữ cửa sổ dòng lệnh mở bằng cách khởi động lại `run_portable.bat` và đọc thông báo lỗi. Gửi toàn bộ nội dung thông báo cùng các bước vừa thực hiện cho người hỗ trợ kỹ thuật.
