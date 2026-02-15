// src/types/index.ts

export interface User {
  id: number; // Matches backend DB ID type (integer)
  email: string;
  username: string;
  createdAt: Date; // ISO date string from backend
  profileImage?: string | null; // Full URL from backend, can be null
}

export interface Product {
  id: number; // Matches backend DB ID type (integer)
  title: string;
  description: string;
  category: string;
  price: number;
  images: string[]; // Array of full image URLs from backend
  sellerId: number; // Matches User.id type
  sellerName: string;
  createdAt: Date; // ISO date string
}

export interface CartItem {
  id?: number; // Cart item's own ID from backend
  productId: number; // Product's ID
  quantity: number;
  product: Product; // Full product details, including full image URLs
  addedAt?: Date; // ISO date string
}

export interface Purchase {
  id: number; // Purchase ID from backend
  userId: number;
  purchaseDate: Date; // ISO date string
  totalAmount: number;
  items: PurchaseItem[];
}

export interface PurchaseItem {
  id: number; // PurchaseItem ID from backend
  productId: number;
  product: Product; // Snapshot of product at time of purchase, with full image URLs
  purchaseDate: Date; // ISO date Date (from parent Purchase)
  quantity: number;
}

export type Category =
  | "All"
  | "Electronics"
  | "Clothing"
  | "Home"
  | "Garden"
  | "Toys"
  | "Books"
  | "Beauty"
  | "Health"
  | "Sports"
  | "Others";

export const CATEGORIES: Category[] = [
  "All",
  "Electronics",
  "Clothing",
  "Home",
  "Garden",
  "Toys",
  "Books",
  "Beauty",
  "Health",
  "Sports",
  "Others",
];

// For paginated product responses from the backend
export interface PaginatedProductsResponse {
  products: Product[];
  total_products: number;
  current_page: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  error?: string; // Optional error field if api.ts might add it
}

// For frontend form state before sending to backend
// Price is string for form input, images are handled separately as File objects
export interface ProductFormInputData {
    title: string;
    description: string;
    category: string;
    price: string; 
}
