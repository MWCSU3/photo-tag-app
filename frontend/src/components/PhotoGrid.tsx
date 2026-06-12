"use client";

import { Photo } from "@/lib/types";
import { PhotoCard } from "./PhotoCard";

interface PhotoGridProps {
  photos: Photo[];
  isLoading: boolean;
  onPhotoClick: (photo: Photo) => void;
}

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden animate-pulse">
      <div className="aspect-square bg-gray-200" />
      <div className="p-3 space-y-2">
        <div className="flex gap-1">
          <div className="h-5 w-12 bg-gray-200 rounded" />
          <div className="h-5 w-16 bg-gray-200 rounded" />
        </div>
        <div className="h-4 w-20 bg-gray-200 rounded" />
      </div>
    </div>
  );
}

export function PhotoGrid({ photos, isLoading, onPhotoClick }: PhotoGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <p className="text-lg font-medium">No photos found</p>
        <p className="text-sm mt-1">Upload some photos or adjust your filters</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
      {photos.map((photo: Photo) => (
        <PhotoCard key={photo.id} photo={photo} onClick={onPhotoClick} />
      ))}
    </div>
  );
}
