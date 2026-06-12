"use client";

import { Photo, TagCategory, Tag } from "@/lib/types";
import { cn } from "@/lib/utils";
import { getImageUrl } from "@/lib/api";
import { Calendar, Users } from "lucide-react";

const categoryColorClasses: Record<TagCategory, { bg: string; text: string }> = {
  [TagCategory.WHO]: { bg: "bg-blue-100", text: "text-blue-800" },
  [TagCategory.FACES]: { bg: "bg-purple-100", text: "text-purple-800" },
  [TagCategory.WHAT]: { bg: "bg-green-100", text: "text-green-800" },
  [TagCategory.WHERE]: { bg: "bg-orange-100", text: "text-orange-800" },
};

interface PhotoCardProps {
  photo: Photo;
  onClick: (photo: Photo) => void;
}

export function PhotoCard({ photo, onClick }: PhotoCardProps) {
  const topTags = photo.tags.slice(0, 4);
  const peopleCount = photo.tags.filter(
    (t: Tag) => t.category === TagCategory.FACES
  ).length;
  const uploadDate = new Date(photo.upload_date).toLocaleDateString();

  return (
    <div
      className={cn(
        "group cursor-pointer rounded-lg border border-gray-200 bg-white overflow-hidden",
        "shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-0.5"
      )}
      onClick={() => onClick(photo)}
    >
      {/* Thumbnail */}
      <div className="relative aspect-square overflow-hidden bg-gray-100">
        <img
          src={getImageUrl(photo.filename)}
          alt={photo.original_filename}
          className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-200"
        />
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-200" />
        {peopleCount > 0 && (
          <div className="absolute top-2 right-2 bg-white/90 rounded-full px-2 py-0.5 flex items-center gap-1 text-xs font-medium text-gray-700">
            <Users size={12} />
            <span>{peopleCount}</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-2">
          {topTags.map((tag: Tag) => {
            const colors = categoryColorClasses[tag.category];
            return (
              <span
                key={tag.id}
                className={cn(
                  "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium",
                  colors.bg,
                  colors.text
                )}
              >
                {tag.value}
              </span>
            );
          })}
          {photo.tags.length > 4 && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
              +{photo.tags.length - 4}
            </span>
          )}
        </div>

        {/* Date */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Calendar size={12} />
          <span>{uploadDate}</span>
        </div>
      </div>
    </div>
  );
}
