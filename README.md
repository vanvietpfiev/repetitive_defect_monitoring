# ✈️ Aircraft Maintenance Reliability Dashboard

Công cụ phân tích hỏng hóc lặp lại cho Technical Department - Vietnam Airlines

## 🎯 Tính năng chính

- **Phân tích Work Orders**: Tự động phân tích dữ liệu từ hệ thống AMOS
- **Phát hiện hỏng hóc lặp lại**: Nhận diện các sự cố chưa được xử lý triệt để
- **Đánh giá hiệu quả khắc phục**: Theo dõi effectiveness của corrective actions
- **Khuyến cáo kỹ thuật**: Đưa ra recommendations dựa trên pattern analysis
- **Sync Google Sheets**: Lưu trữ và chia sẻ đánh giá kỹ thuật

## 🚀 Cài đặt

### Yêu cầu
- Python 3.8+
- pip

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## 📊 Sử dụng

### Chạy local

```bash
streamlit run app.py
```

### Upload dữ liệu

1. Đăng nhập với tài khoản được cấp
2. Upload file Excel từ AMOS system
3. Chọn tùy chọn phân tích (loại bỏ Type 'S' nếu cần)
4. Xem kết quả phân tích và khuyến cáo

## 🔐 Xác thực

Ứng dụng sử dụng `streamlit-authenticator` để bảo mật.

**Tài khoản mặc định:**
- Username: `admin`
- Password: `vna1234`

⚠️ **Lưu ý**: Đổi mật khẩu sau khi deploy production!

## 📁 Cấu trúc project

```
.
├── app.py                    # Main Streamlit application
├── analysis.py               # Core analysis logic
├── requirements.txt          # Python dependencies
├── technical_comments.csv    # Local comment storage
└── .streamlit/
    └── config.toml          # Streamlit configuration
```

## 🛠️ Tech Stack

- **Streamlit**: Web framework
- **Pandas**: Data analysis
- **streamlit-authenticator**: Authentication
- **Altair**: Data visualization
- **openpyxl/xlsxwriter**: Excel processing

## 📝 License

Internal tool for Vietnam Airlines Technical Department

## 👥 Contact

Technical Department - Vietnam Airlines
