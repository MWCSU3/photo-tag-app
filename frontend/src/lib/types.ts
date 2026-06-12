export enum TagCategory {
  WHO = "WHO",
  FACES = "FACES",
  WHAT = "WHAT",
  WHERE = "WHERE",
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Tag {
  id: string;
  category: TagCategory;
  value: string;
  confidence: number;
  bounding_box?: BoundingBox | null;
}

export interface Photo {
  id: string;
  filename: string;
  original_filename: string;
  upload_date: string;
  width: number;
  height: number;
  analyzed: boolean;
  tags: Tag[];
}

export enum SortBy {
  DATE = "date",
  NUM_PEOPLE = "num_people",
  LOCATION = "location",
  CONFIDENCE = "confidence",
}

export enum SortOrder {
  ASC = "asc",
  DESC = "desc",
}

export enum GroupBy {
  DATE = "date",
  LOCATION = "location",
  PERSON = "person",
}

export interface FilterState {
  selectedTags: Record<TagCategory, string[]>;
  sortBy: SortBy;
  sortOrder: SortOrder;
  groupBy: GroupBy | null;
}

export interface FilterParams {
  categories?: string;
  sort_by?: string;
  sort_order?: string;
  group_by?: string;
  page?: number;
  page_size?: number;
}

export interface TagsResponse {
  categories: Record<string, string[]>;
}

export interface PhotosResponse {
  photos: Photo[];
  total: number;
  page: number;
  page_size: number;
}

export const CATEGORY_COLORS: Record<TagCategory, string> = {
  [TagCategory.WHO]: "blue",
  [TagCategory.FACES]: "purple",
  [TagCategory.WHAT]: "green",
  [TagCategory.WHERE]: "orange",
};

export const CATEGORY_LABELS: Record<TagCategory, string> = {
  [TagCategory.WHO]: "Who",
  [TagCategory.FACES]: "Faces",
  [TagCategory.WHAT]: "What",
  [TagCategory.WHERE]: "Where",
};
