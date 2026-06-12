"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TagCategory,
  FilterState,
  SortBy,
  SortOrder,
  GroupBy,
  CATEGORY_LABELS,
} from "@/lib/types";
import { getTags } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  X,
  ArrowUpDown,
  Filter,
  RotateCcw,
  SlidersHorizontal,
} from "lucide-react";

interface FilterPanelProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
}

const categoryColorClasses: Record<TagCategory, { checkbox: string; pill: string }> = {
  [TagCategory.WHO]: {
    checkbox: "accent-blue-600",
    pill: "bg-blue-100 text-blue-800",
  },
  [TagCategory.FACES]: {
    checkbox: "accent-purple-600",
    pill: "bg-purple-100 text-purple-800",
  },
  [TagCategory.WHAT]: {
    checkbox: "accent-green-600",
    pill: "bg-green-100 text-green-800",
  },
  [TagCategory.WHERE]: {
    checkbox: "accent-orange-600",
    pill: "bg-orange-100 text-orange-800",
  },
};

function CategorySection({
  category,
  availableTags,
  selectedTags,
  onToggleTag,
}: {
  category: TagCategory;
  availableTags: string[];
  selectedTags: string[];
  onToggleTag: (category: TagCategory, tag: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const colors = categoryColorClasses[category];

  return (
    <div className="border-b border-gray-100 pb-3">
      <button
        className="flex items-center justify-between w-full py-2 text-sm font-semibold text-gray-700 hover:text-gray-900"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="flex items-center gap-1.5">
          {CATEGORY_LABELS[category]}
          {selectedTags.length > 0 && (
            <span className="text-xs bg-gray-200 text-gray-600 rounded-full px-1.5 py-0.5">
              {selectedTags.length}
            </span>
          )}
        </span>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {expanded && (
        <div className="space-y-1 mt-1">
          {availableTags.length === 0 ? (
            <p className="text-xs text-gray-400 italic pl-1">No tags available</p>
          ) : (
            availableTags.map((tag) => (
              <label
                key={tag}
                className="flex items-center gap-2 px-1 py-0.5 rounded hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedTags.includes(tag)}
                  onChange={() => onToggleTag(category, tag)}
                  className={cn("rounded", colors.checkbox)}
                />
                <span className="text-sm text-gray-700 truncate">{tag}</span>
              </label>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function FilterPanel({ filters, onFiltersChange }: FilterPanelProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: tagsData } = useQuery({
    queryKey: ["tags"],
    queryFn: getTags,
  });

  const categories = tagsData?.categories || {};

  const handleToggleTag = (category: TagCategory, tag: string) => {
    const current = filters.selectedTags[category] || [];
    const updated = current.includes(tag)
      ? current.filter((t) => t !== tag)
      : [...current, tag];

    onFiltersChange({
      ...filters,
      selectedTags: {
        ...filters.selectedTags,
        [category]: updated,
      },
    });
  };

  const handleRemoveTag = (category: TagCategory, tag: string) => {
    const current = filters.selectedTags[category] || [];
    onFiltersChange({
      ...filters,
      selectedTags: {
        ...filters.selectedTags,
        [category]: current.filter((t) => t !== tag),
      },
    });
  };

  const handleReset = () => {
    onFiltersChange({
      selectedTags: {
        [TagCategory.WHO]: [],
        [TagCategory.FACES]: [],
        [TagCategory.WHAT]: [],
        [TagCategory.WHERE]: [],
      },
      sortBy: SortBy.DATE,
      sortOrder: SortOrder.DESC,
      groupBy: null,
    });
  };

  const activeFilterCount = Object.values(filters.selectedTags).reduce(
    (acc, tags) => acc + tags.length,
    0
  );

  const panelContent = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-600" />
          <h2 className="font-semibold text-gray-800">Filters</h2>
          {activeFilterCount > 0 && (
            <span className="text-xs bg-blue-100 text-blue-800 rounded-full px-2 py-0.5">
              {activeFilterCount}
            </span>
          )}
        </div>
        <button
          onClick={handleReset}
          className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <RotateCcw size={12} />
          Reset
        </button>
      </div>

      {/* Active filter pills */}
      {activeFilterCount > 0 && (
        <div className="px-4 py-2 border-b border-gray-100">
          <div className="flex flex-wrap gap-1">
            {Object.entries(filters.selectedTags).map(([cat, tags]) =>
              tags.map((tag) => {
                const colors = categoryColorClasses[cat as TagCategory];
                return (
                  <span
                    key={`${cat}-${tag}`}
                    className={cn(
                      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                      colors.pill
                    )}
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(cat as TagCategory, tag)}
                      className="hover:opacity-70"
                    >
                      <X size={10} />
                    </button>
                  </span>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tag categories */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1">
        {Object.values(TagCategory).map((category) => (
          <CategorySection
            key={category}
            category={category}
            availableTags={categories[category] || []}
            selectedTags={filters.selectedTags[category] || []}
            onToggleTag={handleToggleTag}
          />
        ))}
      </div>

      {/* Sort and Group controls */}
      <div className="border-t border-gray-200 px-4 py-3 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <SlidersHorizontal size={14} className="text-gray-600" />
          <span className="text-sm font-semibold text-gray-700">Sort & Group</span>
        </div>

        {/* Sort By */}
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Sort by
          </label>
          <div className="flex gap-2 mt-1">
            <select
              value={filters.sortBy}
              onChange={(e) =>
                onFiltersChange({ ...filters, sortBy: e.target.value as SortBy })
              }
              className="flex-1 text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={SortBy.DATE}>Date</option>
              <option value={SortBy.NUM_PEOPLE}>People count</option>
              <option value={SortBy.LOCATION}>Location</option>
              <option value={SortBy.CONFIDENCE}>Confidence</option>
            </select>
            <button
              onClick={() =>
                onFiltersChange({
                  ...filters,
                  sortOrder:
                    filters.sortOrder === SortOrder.ASC
                      ? SortOrder.DESC
                      : SortOrder.ASC,
                })
              }
              className={cn(
                "p-1.5 border border-gray-200 rounded-md hover:bg-gray-50",
                filters.sortOrder === SortOrder.DESC && "bg-gray-100"
              )}
              title={`Sort ${filters.sortOrder === SortOrder.ASC ? "ascending" : "descending"}`}
            >
              <ArrowUpDown size={14} />
            </button>
          </div>
        </div>

        {/* Group By */}
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Group by
          </label>
          <select
            value={filters.groupBy || ""}
            onChange={(e) =>
              onFiltersChange({
                ...filters,
                groupBy: (e.target.value as GroupBy) || null,
              })
            }
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 mt-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">None</option>
            <option value={GroupBy.DATE}>Date</option>
            <option value={GroupBy.LOCATION}>Location</option>
            <option value={GroupBy.PERSON}>Person</option>
          </select>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle button */}
      <button
        className="lg:hidden fixed bottom-20 left-4 z-40 bg-blue-600 text-white rounded-full p-3 shadow-lg hover:bg-blue-700 transition-colors"
        onClick={() => setMobileOpen(true)}
      >
        <Filter size={20} />
        {activeFilterCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {activeFilterCount}
          </span>
        )}
      </button>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col w-72 border-r border-gray-200 bg-white h-full">
        {panelContent}
      </aside>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 bottom-0 w-80 max-w-[85vw] bg-white shadow-xl">
            <div className="flex items-center justify-end p-2">
              <button
                onClick={() => setMobileOpen(false)}
                className="p-2 hover:bg-gray-100 rounded-md"
              >
                <X size={20} />
              </button>
            </div>
            {panelContent}
          </div>
        </div>
      )}
    </>
  );
}
