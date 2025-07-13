# Start from an official Python image
FROM python:3.9-slim-buster

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf libmagic1 \          
    # for pdfkit
    #
    libssl-dev \          
    # often needed by cryptography/pycryptodome
    libffi-dev \    
    # often needed by cryptography/pycryptodome
    build-essential \     
    # for compiling numpy/scipy if needed
    #git \                  # if needed
    #nodejs \               # if needed
    #npm \                  # if needed
    # libreoffice          # uncomment if you need LibreOffice
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install \
    geopy \
    django \
    djangorestframework \
    markdown \
    django-filter \
    django-bootstrap4 \
    django-bootstrap-datepicker-plus \
    drf_spectacular \
    django-cors-headers \
    django-extensions \
    psycopg2-binary \
    pandas \
    django-environ \
    scipy \
    pillow \
    pycrypto \
    django-csp \ 
    python-docx \
    pdfkit \
    whitenoise \
    paho-mqtt  \
    gunicorn \
    django \
    djangorestframework \
    requests \
    numpy \
    pandas \
    scipy \
    pycryptodome \
    python-docx \
    pdfkit \
    docx2pdf \ 
    django-filter \
    django-cors-headers bleach python-magic\ 
    gunicorn

# Set the working directory in the container
WORKDIR /app

# Copy your Django project files into the container (including cert.pem & key.pem if needed)
COPY . /app

# (Optional) If you need to collect static files, uncomment the line below:
RUN python manage.py collectstatic --noinput

# Expose port 2000
EXPOSE 5001

# Environment variables will be passed from system environment
ARG MAIL_ID
ARG MAIL_PW
ARG DEBUG
ARG SECRET_KEY
ARG EMAIL_HOST_USER
ARG EMAIL_HOST_PASSWORD
ARG ALLOWED_HOSTS
ARG DB_NAME
ARG DB_USER
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT

ENV MAIL_ID=${MAIL_ID}
ENV MAIL_PW=${MAIL_PW}
ENV DEBUG=${DEBUG}
ENV SECRET_KEY=${SECRET_KEY}
ENV EMAIL_HOST_USER=${EMAIL_HOST_USER}
ENV EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
ENV ALLOWED_HOSTS=${ALLOWED_HOSTS}
ENV DB_NAME=${DB_NAME}
ENV DB_USER=${DB_USER}
ENV DB_PASSWORD=${DB_PASSWORD}
ENV DB_HOST=${DB_HOST}
ENV DB_PORT=${DB_PORT}
# 


# Run gunicorn, binding to 0.0.0.0:2000, and using SSL cert/key
CMD ["python", "em_server.py"]
