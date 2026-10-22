# Hosting krelboyneos.org on your Raspberry Pi

Plan: nginx on the Pi serves the site files on a local-only port. A Cloudflare Tunnel connects that port to krelboyneos.org. You don't open any ports on your router, and your home IP stays hidden. The ISO itself stays on R2, so the Pi only serves a small static site.

Prerequisite: krelboyneos.org must be on Cloudflare (Cloudflare manages its DNS). If you registered it somewhere else, add it as a site in the Cloudflare dashboard first and switch the nameservers.

Run these on the Pi, one step at a time.

## 1. Install nginx

    sudo apt update
    sudo apt install nginx

## 2. Make the web folder

    sudo mkdir -p /var/www/krelboyneos
    sudo chown $USER:$USER /var/www/krelboyneos

## 3. Copy the site to the Pi

From AcidBurn, in the folder holding `index.html`, `style.css` and `img/` (use the Pi's real user and address):

    rsync -av --delete index.html style.css img/ PIUSER@PI-ADDRESS:/var/www/krelboyneos/

If rsync complains about `img/`, copy the folder as `img` explicitly:

    rsync -av index.html style.css PIUSER@PI-ADDRESS:/var/www/krelboyneos/
    rsync -av img/ PIUSER@PI-ADDRESS:/var/www/krelboyneos/img/

## 4. Tell nginx about the site

Create `/etc/nginx/sites-available/krelboyneos` with:

    server {
        listen 127.0.0.1:8080;
        server_name krelboyneos.org www.krelboyneos.org;

        root /var/www/krelboyneos;
        index index.html;

        gzip on;
        gzip_types text/css application/javascript image/svg+xml;

        location /img/ { expires 30d; add_header Cache-Control "public"; }
        location / { try_files $uri $uri/ =404; }
    }

Turn it on and check it:

    sudo ln -s /etc/nginx/sites-available/krelboyneos /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx
    curl -I http://127.0.0.1:8080

`listen 127.0.0.1:8080` means only the Pi itself can reach nginx. The tunnel runs on the Pi, so it can. You should see `HTTP/1.1 200 OK`.

## 5. Create the Cloudflare Tunnel

Follow Cloudflare's dashboard flow (https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/):

1. Cloudflare dashboard > **Networking > Tunnels** > **Create a tunnel**. Name it `krelboyneos-pi`.
2. Pick the Pi's operating system. The dashboard shows an install command with your tunnel token. Copy it and run it on the Pi. Use the one the dashboard gives you, because it has your token in it.
3. When it shows connected, click **Continue**.
4. Add two published applications (**Routes > Add route > Published application**):
   - Subdomain blank, Domain `krelboyneos.org`, Service URL `http://localhost:8080`
   - Subdomain `www`, Domain `krelboyneos.org`, Service URL `http://localhost:8080`
5. The tunnel should show **Healthy**. Open https://krelboyneos.org.

If the dashboard's install command doesn't work on your Pi OS, Cloudflare's apt repository is the fallback. On Debian-based systems (https://pkg.cloudflare.com):

    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
    sudo apt-get update && sudo apt-get install cloudflared

## Updating the site later

Edit the files on AcidBurn and re-run the `rsync` step. No restart is needed.

## Things to do later

- **Download links:** the ISO and checksum are served from `https://dl.krelboyneos.org/`, a custom domain on the R2 bucket. Don't use the bucket's `r2.dev` address in links: Cloudflare rate-limits it and means it for testing.
- **Screenshots:** they live in `img/shots/` as 1600px-wide WebP files. To add or replace one, convert the PNG with `convert shot.png -resize '1600x>' -quality 80 img/shots/NAME.webp` and add a `<figure>` in the Screenshots section of `index.html`.
- **Fonts:** the page loads Orbitron and JetBrains Mono from Google Fonts. To avoid the third-party request, download them and serve them from `img/` or a `fonts/` folder.
