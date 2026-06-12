"use client";

import { useState, useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadPhoto } from "@/lib/api";
import { Photo, Tag, TagCategory } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Upload, X, CheckCircle, Loader2, AlertCircle, FileImage } from "lucide-react";

type UploadStatus = "idle" | "uploading" | "analyzing" | "complete" | "error";

interface UploadItem {
  file: File;
  status: UploadStatus;
  photo?: Photo;
  error?: string;
}

const categoryColorClasses: Record<TagCategory, string> = {
  [TagCategory.WHO]: "bg-blue-100 text-blue-800",
  [TagCategory.FACES]: "bg-purple-100 text-purple-800",
  [TagCategory.WHAT]: "bg-green-100 text-green-800",
  [TagCategory.WHERE]: "bg-orange-100 text-orange-800",
};

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
}

export function UploadModal({ open, onClose }: UploadModalProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: uploadPhoto,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photos"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const processFile = useCallback(
    async (item: UploadItem, index: number) => {
      setItems((prev) =>
        prev.map((it, i) => (i === index ? { ...it, status: "uploading" } : it))
      );

      try {
        // Update to analyzing (the backend does upload + analysis in one step)
        setItems((prev) =>
          prev.map((it, i) => (i === index ? { ...it, status: "analyzing" } : it))
        );

        const photo = await uploadMutation.mutateAsync(item.file);

        setItems((prev) =>
          prev.map((it, i) =>
            i === index ? { ...it, status: "complete", photo } : it
          )
        );
      } catch (err) {
        setItems((prev) =>
          prev.map((it, i) =>
            i === index
              ? { ...it, status: "error", error: err instanceof Error ? err.message : "Upload failed" }
              : it
          )
        );
      }
    },
    [uploadMutation]
  );

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files)
        .filter((f) => f.type.startsWith("image/"))
        .map((file) => ({ file, status: "idle" as UploadStatus }));

      if (newItems.length === 0) return;

      setItems((prev) => {
        const startIndex = prev.length;
        const combined = [...prev, ...newItems];

        // Process each new file sequentially
        newItems.forEach((item, i) => {
          setTimeout(() => processFile(item, startIndex + i), i * 100);
        });

        return combined;
      });
    },
    [processFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleClose = () => {
    setItems([]);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Upload Photos</h2>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded-md transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drop zone */}
        <div className="px-6 py-4">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
              isDragging
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
            )}
          >
            <Upload
              size={32}
              className={cn(
                "mx-auto mb-3",
                isDragging ? "text-blue-500" : "text-gray-400"
              )}
            />
            <p className="text-sm font-medium text-gray-700">
              Drop images here or click to browse
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Supports JPG, PNG, WebP, and GIF
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </div>

        {/* Upload items list */}
        {items.length > 0 && (
          <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-3">
            {items.map((item, index) => (
              <UploadItemRow key={index} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UploadItemRow({ item }: { item: UploadItem }) {
  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex items-center gap-3">
        <FileImage size={20} className="text-gray-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-700 truncate">
            {item.file.name}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            {item.status === "idle" && (
              <span className="text-xs text-gray-500">Waiting...</span>
            )}
            {item.status === "uploading" && (
              <>
                <Loader2 size={12} className="text-blue-500 animate-spin" />
                <span className="text-xs text-blue-600">Uploading...</span>
              </>
            )}
            {item.status === "analyzing" && (
              <>
                <Loader2 size={12} className="text-purple-500 animate-spin" />
                <span className="text-xs text-purple-600">Analyzing...</span>
              </>
            )}
            {item.status === "complete" && (
              <>
                <CheckCircle size={12} className="text-green-500" />
                <span className="text-xs text-green-600">Complete</span>
              </>
            )}
            {item.status === "error" && (
              <>
                <AlertCircle size={12} className="text-red-500" />
                <span className="text-xs text-red-600">{item.error}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Show detected tags after completion */}
      {item.status === "complete" && item.photo && item.photo.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {item.photo.tags.slice(0, 6).map((tag: Tag) => (
            <span
              key={tag.id}
              className={cn(
                "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium",
                categoryColorClasses[tag.category]
              )}
            >
              {tag.value}
            </span>
          ))}
          {item.photo.tags.length > 6 && (
            <span className="text-xs text-gray-500">
              +{item.photo.tags.length - 6} more
            </span>
          )}
        </div>
      )}
    </div>
  );
}
