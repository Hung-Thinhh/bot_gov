# Frontend Dockerfile
FROM nginx:alpine

# Copy static files
COPY index.html /usr/share/nginx/html/
COPY avt.jpg /usr/share/nginx/html/

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Chạy sed để thay thế placeholder bằng biến môi trường BACKEND_URL khi container khởi động
# Nếu BACKEND_URL trống, sed sẽ thay bằng chuỗi rỗng để index.html tự dùng window.location.origin
CMD ["/bin/sh", "-c", "sed -i \"s|BACKEND_URL_PLACEHOLDER|${BACKEND_URL:-}|g\" /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]
