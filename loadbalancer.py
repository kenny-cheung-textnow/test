# nginx_before.conf
server {
  listen 80;
  location / { proxy_pass http://app:3000; }
}
