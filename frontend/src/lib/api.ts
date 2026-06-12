import { Photo, PhotosResponse, TagsResponse, FilterState, TagCategory } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadPhoto(file: File): Promise<Photo> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/photos/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getPhotos(filters: FilterState, page = 1, pageSize = 20): Promise<PhotosResponse> {
  const params = new URLSearchParams();

  // Build categories filter - only include categories that have selections
  const categoriesFilter: Record<string, string[]> = {};
  for (const category of Object.values(TagCategory)) {
    if (filters.selectedTags[category]?.length > 0) {
      categoriesFilter[category] = filters.selectedTags[category];
    }
  }

  if (Object.keys(categoriesFilter).length > 0) {
    params.set("categories", JSON.stringify(categoriesFilter));
  }

  params.set("sort_by", filters.sortBy);
  params.set("sort_order", filters.sortOrder);

  if (filters.groupBy) {
    params.set("group_by", filters.groupBy);
  }

  params.set("page", String(page));
  params.set("page_size", String(pageSize));

  const response = await fetch(`${API_URL}/api/photos?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch photos: ${response.statusText}`);
  }

  return response.json();
}

export async function getPhoto(id: string): Promise<Photo> {
  const response = await fetch(`${API_URL}/api/photos/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch photo: ${response.statusText}`);
  }

  return response.json();
}

export async function getTags(): Promise<TagsResponse> {
  const response = await fetch(`${API_URL}/api/tags`);

  if (!response.ok) {
    throw new Error(`Failed to fetch tags: ${response.statusText}`);
  }

  return response.json();
}

export async function deletePhoto(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/photos/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete photo: ${response.statusText}`);
  }
}

export function getImageUrl(filename: string): string {
  return `${API_URL}/uploads/${filename}`;
}
