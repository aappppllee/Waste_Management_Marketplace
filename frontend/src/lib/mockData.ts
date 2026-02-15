
import { CartItem, Product, PurchaseItem, User } from "@/types";

// Mock users
export const users: User[] = [
  {
    id: 1,
    email: "user1@example.com",
    username: "EcoUser",
    createdAt: new Date("2023-01-01"),
    profileImage: "https://images.unsplash.com/photo-1535268647677-300dbf3d78d1"
  }
];

// Mock products
export const products: Product[] = [
  {
    id: 1,
    title: "Eco-friendly Water Bottle",
    description: "Reusable water bottle made from recycled materials. BPA free and dishwasher safe.",
    category: "Home",
    price: 24.99,
    images: ["https://images.unsplash.com/photo-1618160702438-9b02ab6515c9"],
    sellerId: 1,
    sellerName: "EcoUser",
    createdAt: new Date("2023-05-15")
  },
  {
    id: 2,
    title: "Organic Cotton T-shirt",
    description: "Made with 100% organic cotton, this t-shirt is perfect for everyday wear.",
    category: "Clothing",
    price: 29.99,
    images: ["https://images.unsplash.com/photo-1721322800607-8c38375eef04"],
    sellerId: 1,
    sellerName: "EcoUser",
    createdAt: new Date("2023-06-10")
  },
  {
    id: 3,
    title: "Bamboo Cutting Board",
    description: "Sustainable bamboo cutting board that's durable and easy to clean.",
    category: "Kitchen",
    price: 34.99,
    images: ["https://images.unsplash.com/photo-1582562124811-c09040d0a901"],
    sellerId: 1,
    sellerName: "EcoUser",
    createdAt: new Date("2023-04-22")
  },
  {
    id: 4,
    title: "Solar-Powered Phone Charger",
    description: "Charge your devices on the go with this solar-powered charger.",
    category: "Electronics",
    price: 49.99,
    images: ["https://images.unsplash.com/photo-1493962853295-0fd70327578a"],
    sellerId: 1,
    sellerName: "EcoUser",
    createdAt: new Date("2023-03-30")
  }
];

// Mock cart items
export const cartItems: CartItem[] = [
  {
    productId: 1,
    quantity: 2,
    product: products[0]
  }
];

// Mock purchase history
export const purchaseHistory: PurchaseItem[] = [
  {
    id: 1,
    productId: 2,
    product: products[1],
    purchaseDate: new Date("2023-05-20"),
    quantity: 1
  },
  {
    id: 2,
    productId: 3,
    product: products[2],
    purchaseDate: new Date("2023-06-05"),
    quantity: 1
  }
];

// Local Storage Keys
export const STORAGE_KEYS = {
  USER: "ecofinds-user",
  PRODUCTS: "ecofinds-products",
  CART: "ecofinds-cart",
  PURCHASES: "ecofinds-purchases"
};
