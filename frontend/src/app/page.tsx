"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPhotos, deletePhoto } from "@/lib/api";
import {
  Photo,
  FilterState,
  TagCategory,
  SortBy,
  SortOrder,
} from "@/lib/types";
import { PhotoGrid } from "@/components/PhotoGrid";
import { FilterPanel } from "@/components/FilterPanel";
import { UploadModal } from "@/components/UploadModal";
import { PhotoDetail } from "@/components/PhotoDetail";
import { Plus, Camera } from "lucide-react";

const defaultFilters: FilterState = {
  selectedTags: {
    [TagCategory.WHO]: [],
    [TagCategory.FACES]: [],
    [TagCategory.WHAT]: [],
    [TagCategory.WHERE]: [],
  },
  sortBy: SortBy.DATE,
  sortOrder: SortOrder.DESC,
  groupBy: null,
};

export default function HomePage() {
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["photos", filters],
    queryFn: () => getPhotos(filters),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePhoto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photos"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setSelectedPhoto(null);
    },
  });

  const handleDeletePhoto = (id: string) => {
    if (window.confirm("Are you sure you want to delete this photo?")) {
      deleteMutation.mutate(id);
    }
  };

  const photos = data?.photos || [];

  return (
    <div className="flex h-full flex-1">
      {/* Filter sidebar */}
      <FilterPanel filters={filters} onFiltersChange={setFilters} />

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-3">
            <Camera size={24} className="text-blue-600" />
            <h1 className="text-xl font-bold text-gray-800">PhotoTagger</h1>
          </div>
          <button
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <Plus size={16} />
            <span className="hidden sm:inline">Upload</span>
          </button>
        </header>

        {/* Photo grid area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          <PhotoGrid
            photos={photos}
            isLoading={isLoading}
            onPhotoClick={setSelectedPhoto}
          />
        </div>

        {/* Mobile FAB for upload */}
        <button
          onClick={() => setUploadOpen(true)}
          className="lg:hidden fixed bottom-4 right-4 z-40 bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={24} />
        </button>
      </main>

      {/* Upload Modal */}
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />

      {/* Photo Detail */}
      {selectedPhoto && (
        <PhotoDetail
          photo={selectedPhoto}
          onClose={() => setSelectedPhoto(null)}
          onDelete={handleDeletePhoto}
        />
      )}
    </div>
  );
}
