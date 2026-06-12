"use client";

import { Photo, Tag, TagCategory, CATEGORY_LABELS } from "@/lib/types";
import { getImageUrl } from "@/lib/api";
import { cn } from "@/lib/utils";
import { X, Calendar, FileImage, Maximize2 } from "lucide-react";

const categoryColorClasses: Record<TagCategory, { bg: string; text: string; border: string }> = {
  [TagCategory.WHO]: { bg: "bg-blue-50", text: "text-blue-800", border: "border-blue-200" },
  [TagCategory.FACES]: { bg: "bg-purple-50", text: "text-purple-800", border: "border-purple-200" },
  [TagCategory.WHAT]: { bg: "bg-green-50", text: "text-green-800", border: "border-green-200" },
  [TagCategory.WHERE]: { bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-200" },
};

interface PhotoDetailProps {
  photo: Photo;
  onClose: () => void;
  onDelete: (id: string) => void;
}

export function PhotoDetail({ photo, onClose, onDelete }: PhotoDetailProps) {
  const uploadDate = new Date(photo.upload_date).toLocaleString();
  const tagsByCategory = Object.values(TagCategory).reduce(
    (acc, cat) => {
      acc[cat] = photo.tags.filter((t: Tag) => t.category === cat);
      return acc;
    },
    {} as Record<TagCategory, Tag[]>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800 truncate">
            {photo.original_filename}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onDelete(photo.id)}
              className="text-sm text-red-600 hover:text-red-700 px-3 py-1 rounded-md hover:bg-red-50"
            >
              Delete
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-md transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto flex flex-col md:flex-row">
          {/* Image */}
          <div className="relative md:flex-1 bg-gray-900 flex items-center justify-center min-h-[300px]">
            <img
              src={getImageUrl(photo.filename)}
              alt={photo.original_filename}
              className="max-w-full max-h-[60vh] object-contain"
            />
            {/* Bounding boxes overlay */}
            {photo.tags.some((t: Tag) => t.bounding_box) && (
              <div className="absolute inset-0 pointer-events-none">
                {photo.tags
                  .filter((t: Tag) => t.bounding_box)
                  .map((tag: Tag) => {
                    const bbox = tag.bounding_box!;
                    const colors = categoryColorClasses[tag.category];
                    return (
                      <div
                        key={tag.id}
                        className={cn("absolute border-2", colors.border)}
                        style={{
                          left: `${bbox.x * 100}%`,
                          top: `${bbox.y * 100}%`,
                          width: `${bbox.width * 100}%`,
                          height: `${bbox.height * 100}%`,
                        }}
                      >
                        <span
                          className={cn(
                            "absolute -top-5 left-0 text-[10px] px-1 rounded",
                            colors.bg,
                            colors.text
                          )}
                        >
                          {tag.value}
                        </span>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>

          {/* Details sidebar */}
          <div className="md:w-80 border-t md:border-t-0 md:border-l border-gray-200 overflow-y-auto">
            {/* File info */}
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                File Info
              </h3>
              <div className="space-y-1.5 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <Calendar size={14} />
                  <span>{uploadDate}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Maximize2 size={14} />
                  <span>
                    {photo.width} x {photo.height}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <FileImage size={14} />
                  <span className="truncate">{photo.original_filename}</span>
                </div>
              </div>
            </div>

            {/* Tags by category */}
            <div className="px-4 py-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Detected Tags
              </h3>
              <div className="space-y-4">
                {Object.values(TagCategory).map((category) => {
                  const tags = tagsByCategory[category];
                  if (tags.length === 0) return null;
                  const colors = categoryColorClasses[category];
                  return (
                    <div key={category}>
                      <h4
                        className={cn(
                          "text-xs font-semibold mb-1.5",
                          colors.text
                        )}
                      >
                        {CATEGORY_LABELS[category]}
                      </h4>
                      <div className="space-y-1">
                        {tags.map((tag: Tag) => (
                          <div
                            key={tag.id}
                            className={cn(
                              "flex items-center justify-between px-2 py-1 rounded",
                              colors.bg
                            )}
                          >
                            <span className={cn("text-sm font-medium", colors.text)}>
                              {tag.value}
                            </span>
                            <span className="text-xs text-gray-500">
                              {Math.round(tag.confidence * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {photo.tags.length === 0 && (
                  <p className="text-sm text-gray-400 italic">
                    No tags detected
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
