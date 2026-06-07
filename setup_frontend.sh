#!/bin/bash
# IncidentOS AI Frontend Setup Script
# Run: bash setup_frontend.sh

set -e
echo "🚀 Setting up IncidentOS AI Frontend..."

# 1. Scaffold Next.js app
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --no-eslint \
  --yes

cd frontend

# 2. Install all dependencies
npm install \
  framer-motion \
  lucide-react \
  @tanstack/react-query \
  recharts \
  d3 \
  @types/d3 \
  class-variance-authority \
  clsx \
  tailwind-merge \
  @radix-ui/react-dialog \
  @radix-ui/react-dropdown-menu \
  @radix-ui/react-select \
  @radix-ui/react-tabs \
  @radix-ui/react-tooltip \
  @radix-ui/react-badge \
  @radix-ui/react-separator \
  @radix-ui/react-avatar \
  @radix-ui/react-progress \
  @radix-ui/react-slot \
  tailwindcss-animate \
  next-themes \
  date-fns

echo "✅ Dependencies installed!"
echo "Now run: cd frontend && npm run dev"
