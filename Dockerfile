# ---------------------------------------------------------------------------
# Automated CI/CD Deployment Pipeline using AWS and Docker
# Application image: static site served by Nginx.
#
# Single-stage build on purpose. A multi-stage build only pays off when you
# compile something (Node, Java, Go). Nginx serving static files needs no
# build stage, and adding one would be cargo-cult complexity.
# ---------------------------------------------------------------------------

# Base image: official Nginx on Alpine Linux (~50 MB, far smaller than the
# Debian-based tag). Pinning the minor version keeps builds reproducible --
# `nginx:alpine` would silently jump major versions on you.
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="devops-cicd-demo"
LABEL org.opencontainers.image.description="Static site served by Nginx, deployed via GitHub Actions to AWS ECR and EC2"

# Remove the stock "Welcome to nginx" page so we know what we see is ours.
RUN rm -rf /usr/share/nginx/html/*

# Copy our application files into the directory Nginx serves from.
# Trailing slash on site/ means "contents of site/", not the folder itself.
COPY site/ /usr/share/nginx/html/

# Health endpoint for the CI smoke test and for Docker healthchecks later.
# Nginx serves static files, so a plain text file IS a working endpoint.
RUN printf 'ok\n' > /usr/share/nginx/html/healthz

# Documentation only -- EXPOSE does not actually publish the port.
# Ports are mapped at runtime with `docker run -p`.
EXPOSE 80

# The official image already sets this CMD; stated explicitly so the
# behaviour (foreground process, container stays alive) is visible in review.
# "daemon off" is required: if Nginx daemonises, PID 1 exits and the
# container stops immediately.
CMD ["nginx", "-g", "daemon off;"]
