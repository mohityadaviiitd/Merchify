# Merchify

## Live Website

> [http://ec2-13-233-212-112.ap-south-1.compute.amazonaws.com:3000]

---

## Local Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/mohityadaviiitd/Merchify.git
cd merchify
```

### 2. Environment Variables

#### Backend (.env)

Create a `.env` file in the project root with the following (update values as needed):

```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=ap-south-1
STRIPE_SECRET_KEY=your_stripe_secret
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
FRONTEND_BASE_URL=http://localhost:3000
POSTGRES_DB=merchify
POSTGRES_USER=merchifyuser
POSTGRES_PASSWORD=strongpassword
DB_HOST=db
DB_PORT=5432
```

#### Frontend (frontend/.env.local)

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable
```

### 3. Update API Links in Code

- The backend API base URL is set via `NEXT_PUBLIC_API_BASE` in `frontend/.env.local`.
- Stripe keys are set in both backend `.env` and frontend `.env.local`.
- For production, update these to your deployed URLs and keys.

### 4. Run with Docker Compose

```bash
docker-compose up --build
```

This will start three containers: Postgres (db), Django backend (backend), and Next.js frontend (frontend).

---

## Deployment (How this app is deployed)

### Sharding on EC2

If you want to test shard and replica behavior on an EC2 instance instead of RDS, see [EC2_SHARDING_GUIDE.md](EC2_SHARDING_GUIDE.md).

1. **Create an AWS EC2 instance** (Amazon Linux 2 recommended).
2. **Install Docker & Docker Compose** on Amazon Linux:
	 - Update packages:
		 ```bash
		 sudo yum update -y
		 ```
	 - Install Docker:
		 ```bash
		 sudo amazon-linux-extras install docker -y
		 sudo service docker start
		 sudo usermod -a -G docker ec2-user
		 ```
		 (Log out and back in for group changes to take effect.)
	 - Install Docker Compose:
		 ```bash
		 sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
		 sudo chmod +x /usr/local/bin/docker-compose
		 docker-compose --version
		 ```
3. **Clone the repository** on the EC2 instance:
	 ```bash
	 git clone https://github.com/mohityadaviiitd/Merchify.git
	 cd Merchify
	 ```
4. **Add your .env and frontend/.env.local files** with production values.
5. **Run the containers**:
	 ```bash
	 docker-compose up -d --build
	 ```
---

## Frontend User Guide

### Main Paths

- `/` — Home page, links to products and admin dashboard
- `/register` — Register as user or admin
- `/login` — Login for users/admins
- `/products` — Browse all products (add/edit/delete if admin)
- `/cart` — View your cart (must be logged in)
- `/checkout` — Checkout and pay (Stripe integration)
- `/checkout-success` — Order success page after payment
- `/admin-dashboard` — Admin analytics dashboard (requires admin login)

### User Flow

1. **Register**: Go to `/register`, fill in details, choose user or admin role.
2. **Login**: Go to `/login` and enter credentials.
3. **Browse Products**: `/products` shows all available products. Admins can add/edit/delete.
4. **Add to Cart**: Add products to your cart from the products page.
5. **View Cart**: `/cart` shows your selected items and total price.
6. **Checkout**: `/checkout` creates an order and redirects to Stripe for payment.
7. **Order Success**: After payment, `/checkout-success` thanks you and redirects to products.
8. **Admin Dashboard**: `/admin-dashboard` shows stats, revenue, and top products (admin only).

---