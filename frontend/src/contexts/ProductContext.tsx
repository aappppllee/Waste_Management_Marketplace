// src/contexts/ProductContext.tsx
import React, { createContext, useState, useContext, useEffect, useCallback } from "react";
import { Category, Product, PaginatedProductsResponse, ProductFormInputData } from "@/types";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { useAuth } from "./AuthContext";

interface ProductContextType {
  products: Product[];
  filteredProducts: Product[];
  userProducts: Product[];
  isLoading: boolean;
  currentPage: number;
  totalPages: number;
  totalProducts: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
  setPage: (page: number) => void;
  activeCategory: Category;
  searchQuery: string;
  setActiveCategory: (category: Category) => void;
  setSearchQuery: (query: string) => void;
  fetchProducts: (page?: number, category?: Category, query?: string, keepCurrentProductsOnError?: boolean) => Promise<void>;
  fetchUserProducts: () => Promise<void>;
  getProductById: (id: string) => Promise<Product | undefined>;
  addProduct: (
    productData: ProductFormInputData, // Uses ProductFormInputData for form values
    imageFiles?: FileList | File[] | null
  ) => Promise<Product | null>;
  updateProduct: (
    id: string, 
    productData: Partial<ProductFormInputData>, // Uses ProductFormInputData
    newImageFiles?: FileList | File[] | null,
    existingImageUrlsToKeep?: string[]
  ) => Promise<boolean>;
  deleteProduct: (id: string) => Promise<boolean>;
}

const ProductContext = createContext<ProductContextType | null>(null);
const PRODUCTS_PER_PAGE = 8;

export function ProductProvider({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]); // Initialize state
  const [userProducts, setUserProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [hasNextPage, setHasNextPage] = useState<boolean>(false);
  const [hasPrevPage, setHasPrevPage] = useState<boolean>(false);
  const [activeCategory, setActiveCategoryState] = useState<Category>("All");
  const [searchQuery, setSearchQueryState] = useState<string>("");
  const { toast } = useToast();

  const fetchProducts = useCallback(async (page: number = 1, category: Category = activeCategory, query: string = searchQuery, keepCurrentProductsOnError: boolean = false) => {
    setIsLoading(true);
    const response = await api.getProducts(category, query, page, PRODUCTS_PER_PAGE);
    setIsLoading(false);
    if (response && response.products && Array.isArray(response.products) && !response.error) {
      const paginatedData = response as PaginatedProductsResponse;
      setProducts(paginatedData.products);
      setCurrentPage(paginatedData.current_page || 1);
      setTotalPages(paginatedData.total_pages || 1);
      setTotalProducts(paginatedData.total_products || 0);
      setHasNextPage(paginatedData.has_next || false);
      setHasPrevPage(paginatedData.has_prev || false);
    } else {
      toast({ title: "Error fetching products", description: String(response.error || "Could not load products."), variant: "destructive" });
      if (!keepCurrentProductsOnError) {
        setProducts([]); setCurrentPage(1); setTotalPages(1); setTotalProducts(0); setHasNextPage(false); setHasPrevPage(false);
      }
    }
  }, [activeCategory, searchQuery, toast]);

  const fetchUserProducts = useCallback(async () => {
    if (!currentUser) { setUserProducts([]); return; }
    setIsLoading(true);
    const response = await api.getMyListings();
    setIsLoading(false);
    if (response && response.products && Array.isArray(response.products) && !response.error) {
        setUserProducts(response.products);
    } else {
        toast({ title: "Error", description: String(response.error || "Could not fetch your listings."), variant: "destructive" });
        setUserProducts([]);
    }
  }, [currentUser, toast]);

  useEffect(() => {
    fetchProducts(1, "All", "");
    if (currentUser) { fetchUserProducts(); }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser]); // Re-fetch user products if user changes

  const setPage = (page: number) => {
    if (page > 0 && page <= totalPages && page !== currentPage) {
      fetchProducts(page, activeCategory, searchQuery);
    }
  };
  const setActiveCategory = (category: Category) => {
    setActiveCategoryState(category);
    fetchProducts(1, category, searchQuery);
  };
  const setSearchQuery = (query: string) => {
    setSearchQueryState(query);
    fetchProducts(1, activeCategory, query);
  };

  const getProductById = async (id: string): Promise<Product | undefined> => {
    const productIdNumber = Number(id);
    const localProduct = products.find(p => p.id === productIdNumber) || userProducts.find(p => p.id === productIdNumber);
    if (localProduct) return localProduct;
    setIsLoading(true);
    const response = await api.getProductById(id);
    setIsLoading(false);
    if (response && !response.error && (response as Product).id) { return response as Product; }
    else { toast({ title: "Error", description: String(response.error || "Product not found."), variant: "destructive" }); return undefined; }
  };

  const addProduct = async (
    productData: ProductFormInputData,
    imageFiles?: FileList | File[] | null
  ): Promise<Product | null> => {
    if (!currentUser) {
      toast({ title: "Authentication Error", description: "You must be logged in to add a product.", variant: "destructive" });
      return null;
    }
    setIsLoading(true);
    const formData = new FormData();
    formData.append('title', productData.title);
    formData.append('description', productData.description);
    formData.append('category', productData.category);
    formData.append('price', productData.price); // Backend expects string, will convert to float

    if (imageFiles) {
      const files = Array.from(imageFiles); // Ensure it's an array
      for (let i = 0; i < files.length; i++) {
        formData.append('images', files[i]);
      }
    }

    const response = await api.createProduct(formData); // api.ts handles isFormData
    setIsLoading(false);

    if (response && !response.error && (response as Product).id) {
      toast({ title: "Success", description: "Product added successfully!" });
      await fetchUserProducts();
      await fetchProducts(1, "All", ""); // Refresh to page 1
      return response as Product;
    } else {
      toast({ title: "Error", description: String(response.error || "Could not add product."), variant: "destructive" });
      return null;
    }
  };

  const updateProduct = async (
    id: string, 
    productData: Partial<ProductFormInputData>,
    newImageFiles?: FileList | File[] | null,
    existingImageUrlsToKeep?: string[]
  ): Promise<boolean> => {
    setIsLoading(true);
    const formData = new FormData();
    if (productData.title) formData.append('title', productData.title);
    if (productData.description) formData.append('description', productData.description);
    if (productData.category) formData.append('category', productData.category);
    if (productData.price) formData.append('price', productData.price);

    // Send existing images to keep as a JSON string array of their URLs/filenames
    formData.append('existingImages', JSON.stringify(existingImageUrlsToKeep || []));

    if (newImageFiles) {
      const files = Array.from(newImageFiles);
      for (let i = 0; i < files.length; i++) {
        formData.append('images', files[i]);
      }
    }
    
    const response = await api.updateProduct(id, formData);
    setIsLoading(false);

    if (response && !response.error && (response as Product).id) {
      const updatedProduct = response as Product;
      toast({ title: "Success", description: "Product updated successfully!" });
      const productIdNumber = Number(id);
      setUserProducts(prev => prev.map(p => p.id === productIdNumber ? { ...p, ...updatedProduct } : p));
      setProducts(prev => prev.map(p => p.id === productIdNumber ? { ...p, ...updatedProduct } : p));
      // Optionally refetch for full consistency, though optimistic update improves UI speed
      // await fetchUserProducts();
      // await fetchProducts(currentPage, activeCategory, searchQuery);
      return true;
    } else {
      toast({ title: "Error", description: String(response.error || "Could not update product."), variant: "destructive" });
      return false;
    }
  };

  const deleteProduct = async (id: string): Promise<boolean> => {
    setIsLoading(true);
    const response = await api.deleteProduct(id);
    setIsLoading(false);
    if (response && response.msg && !response.error) {
      toast({ title: "Success", description: String(response.msg) });
      const productIdNumber = Number(id);
      setUserProducts(prev => prev.filter(p => p.id !== productIdNumber));
      setProducts(prev => prev.filter(p => p.id !== productIdNumber));
      
      await fetchUserProducts(); 
      // Pass true to keep existing products if refetch fails, to avoid flicker after optimistic update
      await fetchProducts(currentPage, activeCategory, searchQuery, true); 
      
      // Check if current page for general products became empty
      const remainingProductsOnPage = products.filter(p => p.id !== productIdNumber);
      if (remainingProductsOnPage.length === 0 && currentPage > 1) {
        await fetchProducts(currentPage - 1, activeCategory, searchQuery, true);
      } else if (remainingProductsOnPage.length === 0 && currentPage === 1 && totalProducts > 0) {
        // If it was the only page and now empty, but there were products, refetch might show empty state
        // The totalProducts count will be updated by the fetchProducts call.
      }
      return true;
    } else {
      toast({ title: "Error", description: String(response.error || "Could not delete product."), variant: "destructive" });
      return false;
    }
  };

  const value = {
    products, userProducts, isLoading, currentPage, totalPages, totalProducts, hasNextPage, hasPrevPage, setPage,
    activeCategory, searchQuery, setActiveCategory, setSearchQuery, fetchProducts, fetchUserProducts,
    getProductById, addProduct, updateProduct, deleteProduct,
  };
  return <ProductContext.Provider value={value}>{children}</ProductContext.Provider>;
}

export const useProducts = (): ProductContextType => {
  const context = useContext(ProductContext);
  if (!context) { throw new Error("useProducts must be used within a ProductProvider"); }
  return context;
};
