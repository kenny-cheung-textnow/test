# nginx_after.conf
server {
  listen 443 ssl http2;
  server_name example.com;
  ssl_certificate     /etc/ssl/fullchain.pem;
  ssl_certificate_key /etc/ssl/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

  # Size/time limits
  client_max_body_size 2m;
  proxy_read_timeout 30s;
  proxy_send_timeout 30s;

  # Real IP (behind CDN/ELB adjust the header accordingly)
  real_ip_header X-Forwarded-For;

  # Simple per-IP rate limit (burst OK, sustained abuse blocked)
  limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;

  location /login {
    limit_req zone=login burst=20 nodelay;
    proxy_pass http://app:3000;
  }

  location / {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass http://app:3000;
  }
}

# Optional HTTP->HTTPS redirect
server {
  listen 80;
  return 301 https://$host$request_uri;
}
