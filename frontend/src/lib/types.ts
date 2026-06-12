export enum TagCategory {
  WHO = "WHO",
  FACES = "FACES",
  WHAT = "WHAT",
  WHERE = "WHERE",
}

export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
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
  DATE = "upload_date",
  // TODO: NUM_PEOPLE, LOCATION, CONFIDENCE require computed columns or
  // additional backend support. Mapped to upload_date as fallback for now.
  NUM_PEOPLE = "upload_date",
  LOCATION = "upload_date",
  CONFIDENCE = "upload_date",
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
