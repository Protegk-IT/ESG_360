import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ChevronDown,
  ChevronRight,
  FolderTree,
  Layers3,
  Plus,
  RefreshCw,
  Search,
  Tag,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import TopicLibraryApi from "@/api/materiality/TopicLibraryApi";

import type {
  TopicCategory,
  MaterialTopic,
  MaterialSubTopic,
} from "@/types/materiality/materiality";

import TopicLibraryDialog, {
  type TopicLibraryDialogMode,
} from "./TopicLibraryDialog";


/* ==========================================================
   TYPES
========================================================== */

type StatusFilter =
  | "All"
  | "Active"
  | "Inactive";


/* ==========================================================
   COMPONENT
========================================================== */

export default function TopicLibrary() {

  /* ========================================================
     DATA
  ======================================================== */

  const [categories, setCategories] =
    useState<TopicCategory[]>([]);

  const [topics, setTopics] =
    useState<MaterialTopic[]>([]);

  const [subTopics, setSubTopics] =
    useState<MaterialSubTopic[]>([]);


  /* ========================================================
     UI STATE
  ======================================================== */

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("All");


  /* ========================================================
     TREE STATE
  ======================================================== */

  const [expandedCategories, setExpandedCategories] =
    useState<Set<string>>(
      new Set()
    );

  const [expandedTopics, setExpandedTopics] =
    useState<Set<string>>(
      new Set()
    );


  /* ========================================================
     DIALOG STATE
  ======================================================== */

  const [dialogMode, setDialogMode] =
    useState<TopicLibraryDialogMode>(
      null
    );

  const [selectedCategory, setSelectedCategory] =
    useState<TopicCategory | null>(
      null
    );

  const [selectedTopic, setSelectedTopic] =
    useState<MaterialTopic | null>(
      null
    );


  /* ========================================================
     LOAD LIBRARY
  ======================================================== */

  const loadLibrary = useCallback(() => {

    setLoading(true);
    setError(null);

    Promise.all([
      TopicLibraryApi.getCategories(),
      TopicLibraryApi.getTopics(),
      TopicLibraryApi.getSubTopics(),
    ])
      .then(
        ([
          categoryResponse,
          topicResponse,
          subTopicResponse,
        ]) => {

          setCategories(
            categoryResponse.data
          );

          setTopics(
            topicResponse.data
          );

          setSubTopics(
            subTopicResponse.data
          );

        }
      )
      .catch((error) => {

        console.error(
          "Failed to load topic library:",
          error
        );

        setError(
          "Unable to load the topic library."
        );

      })
      .finally(() => {

        setLoading(false);

      });

  }, []);


  /* ========================================================
     INITIAL LOAD
  ======================================================== */

useEffect(() => {
  const load = () => {
    loadLibrary();
  };

  load();
}, [loadLibrary]);


  /* ========================================================
     TOPICS BY CATEGORY
  ======================================================== */

  const topicsByCategory = useMemo(() => {

    const map = new Map<
      string,
      MaterialTopic[]
    >();

    topics.forEach((topic) => {

      const existing =
        map.get(topic.category) ?? [];

      existing.push(topic);

      map.set(
        topic.category,
        existing
      );

    });

    return map;

  }, [topics]);


  /* ========================================================
     SUB-TOPICS BY TOPIC
  ======================================================== */

  const subTopicsByTopic = useMemo(() => {

    const map = new Map<
      string,
      MaterialSubTopic[]
    >();

    subTopics.forEach((subTopic) => {

      const existing =
        map.get(subTopic.topic) ?? [];

      existing.push(subTopic);

      map.set(
        subTopic.topic,
        existing
      );

    });

    return map;

  }, [subTopics]);


  /* ========================================================
     SORT DATA
  ======================================================== */

  const sortTopics = (
    topicList: MaterialTopic[]
  ) => {

    return [...topicList].sort(
      (a, b) =>
        a.display_order -
          b.display_order ||
        a.code - b.code ||
        a.name.localeCompare(
          b.name
        )
    );

  };


  const sortSubTopics = (
    subTopicList: MaterialSubTopic[]
  ) => {

    return [...subTopicList].sort(
      (a, b) =>
        a.display_order -
          b.display_order ||
        a.code.localeCompare(
          b.code
        ) ||
        a.name.localeCompare(
          b.name
        )
    );

  };


  /* ========================================================
     SEARCH + STATUS MATCHING
  ======================================================== */

  const matchesTopic = (
    topic: MaterialTopic
  ) => {

    const keyword =
      search.trim().toLowerCase();

    const topicSubTopics =
      subTopicsByTopic.get(
        topic.id
      ) ?? [];

    const matchesSearch =
      !keyword ||
      topic.name
        .toLowerCase()
        .includes(keyword) ||
      topic.description
        .toLowerCase()
        .includes(keyword) ||
      String(topic.code)
        .includes(keyword) ||
      topicSubTopics.some(
        (subTopic) =>
          subTopic.name
            .toLowerCase()
            .includes(keyword) ||
          subTopic.description
            .toLowerCase()
            .includes(keyword) ||
          subTopic.code
            .toLowerCase()
            .includes(keyword)
      );

    const matchesStatus =
      statusFilter === "All" ||
      (statusFilter === "Active" &&
        topic.is_active) ||
      (statusFilter === "Inactive" &&
        !topic.is_active);

    return (
      matchesSearch &&
      matchesStatus
    );

  };


  /* ========================================================
     FILTERED CATEGORIES
  ======================================================== */

  const filteredCategories = useMemo(() => {

    const keyword =
      search.trim().toLowerCase();

    return categories.filter(
      (category) => {

        const categoryTopics =
          topicsByCategory.get(
            category.id
          ) ?? [];

        const categoryMatchesSearch =
          !keyword ||
          category.name
            .toLowerCase()
            .includes(keyword) ||
          category.code
            .toLowerCase()
            .includes(keyword);


        const visibleTopics =
          categoryTopics.filter(
            (topic) => {

              const topicSubTopics =
                subTopicsByTopic.get(
                  topic.id
                ) ?? [];


              const topicMatchesSearch =
                !keyword ||
                topic.name
                  .toLowerCase()
                  .includes(keyword) ||
                topic.description
                  .toLowerCase()
                  .includes(keyword) ||
                String(topic.code)
                  .includes(keyword) ||
                topicSubTopics.some(
                  (subTopic) =>
                    subTopic.name
                      .toLowerCase()
                      .includes(keyword) ||
                    subTopic.description
                      .toLowerCase()
                      .includes(keyword) ||
                    subTopic.code
                      .toLowerCase()
                      .includes(keyword)
                );


              const topicMatchesStatus =
                statusFilter === "All" ||
                (
                  statusFilter === "Active" &&
                  topic.is_active
                ) ||
                (
                  statusFilter === "Inactive" &&
                  !topic.is_active
                );


              return (
                topicMatchesSearch &&
                topicMatchesStatus
              );

            }
          );


        return (
          categoryMatchesSearch ||
          visibleTopics.length > 0
        );

      }
    );

  }, [
    categories,
    topicsByCategory,
    subTopicsByTopic,
    search,
    statusFilter,
  ]);


  /* ========================================================
     AUTO-EXPAND ON SEARCH
  ======================================================== */
useEffect(() => {
  const autoExpand = () => {
    const keyword = search.trim();

    if (!keyword) {
      return;
    }

    // While actively searching, open every category/topic
    // that currently has a visible match so results aren't
    // hidden behind a collapsed branch.

    setExpandedCategories(
      new Set(
        filteredCategories.map((category) => category.id),
      ),
    );

    setExpandedTopics((previous) => {
      const next = new Set(previous);

      topics.forEach((topic) => {
        if (matchesTopic(topic)) {
          next.add(topic.id);
        }
      });

      return next;
    });
  };

  autoExpand();

  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [search, statusFilter]);

  /* ========================================================
     TOGGLE CATEGORY
  ======================================================== */

  const toggleCategory = (
    categoryId: string
  ) => {

    setExpandedCategories(
      (previous) => {

        const next =
          new Set(previous);

        if (
          next.has(categoryId)
        ) {
          next.delete(categoryId);
        } else {
          next.add(categoryId);
        }

        return next;

      }
    );

  };


  /* ========================================================
     TOGGLE TOPIC
  ======================================================== */

  const toggleTopic = (
    topicId: string
  ) => {

    setExpandedTopics(
      (previous) => {

        const next =
          new Set(previous);

        if (
          next.has(topicId)
        ) {
          next.delete(topicId);
        } else {
          next.add(topicId);
        }

        return next;

      }
    );

  };


  /* ========================================================
     EXPAND / COLLAPSE ALL
  ======================================================== */

  const expandAll = () => {

    setExpandedCategories(
      new Set(
        filteredCategories.map(
          (category) => category.id
        )
      )
    );

    setExpandedTopics(
      new Set(
        topics.map(
          (topic) => topic.id
        )
      )
    );

  };


  const collapseAll = () => {

    setExpandedCategories(new Set());
    setExpandedTopics(new Set());

  };


  /* ========================================================
     ADD CATEGORY
  ======================================================== */

  const handleAddCategory = () => {

    setSelectedCategory(null);
    setSelectedTopic(null);

    setDialogMode(
      "category"
    );

  };


  /* ========================================================
     ADD TOPIC
  ======================================================== */

  const handleAddTopic = (
    category: TopicCategory
  ) => {

    setSelectedCategory(
      category
    );

    setSelectedTopic(null);

    setDialogMode(
      "topic"
    );

  };


  /* ========================================================
     ADD SUB-TOPIC
  ======================================================== */

  const handleAddSubTopic = (
    topic: MaterialTopic
  ) => {

    setSelectedCategory(
      categories.find(
        (category) =>
          category.id ===
          topic.category
      ) ?? null
    );

    setSelectedTopic(
      topic
    );

    setDialogMode(
      "subtopic"
    );

  };


  /* ========================================================
     CLOSE DIALOG
  ======================================================== */

  const handleDialogClose = () => {

    setDialogMode(null);
    setSelectedCategory(null);
    setSelectedTopic(null);

  };


  /* ========================================================
     STATUS BADGE
  ======================================================== */

  const renderStatusBadge = (
    isActive: boolean
  ) => {

    return (
      <Badge
        className={
          isActive
            ? "border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-50"
            : "border border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-100"
        }
      >
        {isActive
          ? "Active"
          : "Inactive"}
      </Badge>
    );

  };


  /* ========================================================
     CATEGORY BADGE
  ======================================================== */

  const renderCategoryBadge = (
    code: TopicCategory["code"]
  ) => {

    const label =
      code === "E"
        ? "Environmental"
        : code === "S"
          ? "Social"
          : "Governance";

    return (
      <Badge
        className="
          border
          border-indigo-200
          bg-indigo-50
          text-indigo-700
          hover:bg-indigo-50
        "
      >
        {label}
      </Badge>
    );

  };


  /* ========================================================
     EMPTY STATE
  ======================================================== */

  const renderEmptyState = () => {

    if (loading) {
      return (
        <div
          className="
            flex
            min-h-[280px]
            items-center
            justify-center
            text-sm
            text-muted-foreground
          "
        >
          Loading topic library...
        </div>
      );
    }

    if (error) {
      return (
        <div
          className="
            flex
            min-h-[280px]
            flex-col
            items-center
            justify-center
            gap-4
          "
        >

          <p className="text-sm text-red-600">
            {error}
          </p>

          <Button
            variant="outline"
            onClick={loadLibrary}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>

        </div>
      );
    }

    if (
      filteredCategories.length === 0
    ) {
      return (
        <div
          className="
            flex
            min-h-[280px]
            flex-col
            items-center
            justify-center
            gap-3
          "
        >

          <FolderTree
            className="
              h-10
              w-10
              text-slate-300
            "
          />

          <div className="text-center">

            <p className="font-medium text-slate-700">
              No topics found
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Try changing your search or
              status filter.
            </p>

          </div>

        </div>
      );
    }

    return null;
  };


  /* ========================================================
     RENDER SUB-TOPIC (TREE LEAF)
  ======================================================== */

  const renderSubTopic = (
  subTopic: MaterialSubTopic,
  isLast: boolean
) => {
  return (
    <div
      key={subTopic.id}
      className="relative pl-6 pb-3 last:pb-0"
    >
      {/* Horizontal connector */}
      <span
        className="
          pointer-events-none
          absolute
          left-0
          top-6
          h-px
          w-6
          bg-slate-200
        "
      />

      {/* Vertical connector */}
      {!isLast && (
        <span
          className="
            pointer-events-none
            absolute
            left-0
            top-6
            bottom-0
            w-px
            bg-slate-200
          "
        />
      )}

      <div
        className="
          flex
          items-center
          justify-between
          gap-4
          rounded-lg
          border
          border-slate-100
          bg-slate-50/70
          px-4
          py-3
          transition-colors
          hover:border-slate-200
          hover:bg-slate-50
        "
      >
        <div className="flex min-w-0 items-center gap-3">
          <div
            className="
              flex
              h-8
              w-8
              shrink-0
              items-center
              justify-center
              rounded-md
              bg-white
              text-slate-500
              shadow-sm
            "
          >
            <Tag className="h-4 w-4" />
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="
                  text-xs
                  font-semibold
                  text-[#4A3FD6]
                "
              >
                {subTopic.code}
              </span>

              <span
                className="
                  truncate
                  text-sm
                  font-medium
                  text-slate-800
                "
              >
                {subTopic.name}
              </span>
            </div>

            {subTopic.description && (
              <p
                className="
                  mt-1
                  line-clamp-2
                  text-xs
                  text-slate-500
                "
              >
                {subTopic.description}
              </p>
            )}
          </div>
        </div>

        <div className="shrink-0">
          {renderStatusBadge(subTopic.is_active)}
        </div>
      </div>
    </div>
  );
};


  /* ========================================================
     RENDER TOPIC (TREE BRANCH)
  ======================================================== */

 const renderTopic = (
  topic: MaterialTopic,
  isLast: boolean
) => {
  const children = sortSubTopics(
    subTopicsByTopic.get(topic.id) ?? []
  );

  const expanded = expandedTopics.has(topic.id);

  return (
    <div
      key={topic.id}
      className="relative pl-6 pb-4 last:pb-0"
    >
      {/* Horizontal connector from category trunk to topic */}
      <span
        className="
          pointer-events-none
          absolute
          left-0
          top-6
          h-px
          w-6
          bg-slate-200
        "
      />

      {/* Vertical connector between topics */}
      {!isLast && (
        <span
          className="
            pointer-events-none
            absolute
            left-0
            top-6
            bottom-0
            w-px
            bg-slate-200
          "
        />
      )}

      <div
        className="
          flex
          items-center
          justify-between
          gap-4
          rounded-xl
          border
          border-slate-200
          bg-white
          px-4
          py-3
          shadow-sm
          transition-all
          hover:border-slate-300
        "
      >
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={() => toggleTopic(topic.id)}
            disabled={children.length === 0}
            className="
              flex
              h-8
              w-8
              shrink-0
              items-center
              justify-center
              rounded-md
              text-slate-500
              hover:bg-slate-100
              disabled:cursor-default
              disabled:opacity-30
              disabled:hover:bg-transparent
            "
            aria-label={
              expanded
                ? "Collapse topic"
                : "Expand topic"
            }
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          <div
            className="
              flex
              h-9
              w-9
              shrink-0
              items-center
              justify-center
              rounded-lg
              bg-indigo-50
              text-[#4A3FD6]
            "
          >
            <Layers3 className="h-4 w-4" />
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="
                  text-xs
                  font-semibold
                  text-[#4A3FD6]
                "
              >
                {topic.code}
              </span>

              <span
                className="
                  truncate
                  text-sm
                  font-semibold
                  text-slate-900
                "
              >
                {topic.name}
              </span>

              {renderStatusBadge(topic.is_active)}
            </div>

            {topic.description && (
              <p
                className="
                  mt-1
                  line-clamp-1
                  text-xs
                  text-slate-500
                "
              >
                {topic.description}
              </p>
            )}
          </div>
        </div>

        <div
          className="
            flex
            shrink-0
            items-center
            gap-2
          "
        >
          <span
            className="
              hidden
              rounded-full
              bg-slate-100
              px-2.5
              py-1
              text-xs
              text-slate-600
              sm:inline-flex
            "
          >
            {children.length}{" "}
            {children.length === 1
              ? "sub-topic"
              : "sub-topics"}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAddSubTopic(topic)}
          >
            <Plus className="mr-1.5 h-4 w-4" />

            <span className="hidden sm:inline">
              Add Sub-topic
            </span>

            <span className="sm:hidden">
              Add
            </span>
          </Button>
        </div>
      </div>

      {/* Sub-topic tree */}
      {expanded && children.length > 0 && (
        <div
          className="
            relative
            ml-4
            mt-3
            pl-6
          "
        >
          {children.map((subTopic, index) =>
            renderSubTopic(
              subTopic,
              index === children.length - 1
            )
          )}
        </div>
      )}
    </div>
  );
};


  /* ========================================================
     RENDER CATEGORY (TREE ROOT)
  ======================================================== */

  const renderCategory = (
    category: TopicCategory
  ) => {

    const categoryTopics =
      sortTopics(
        (
          topicsByCategory.get(
            category.id
          ) ?? []
        ).filter(
          matchesTopic
        )
      );

    const expanded =
      expandedCategories.has(
        category.id
      );

    return (
      <div
        key={category.id}
        className="
          overflow-hidden
          rounded-xl
          border
          border-slate-200
          bg-white
          shadow-sm
        "
      >

        {/* ==================================================
            CATEGORY HEADER
        ================================================== */}

        <div
          className="
            flex
            items-center
            justify-between
            gap-4
            border-b
            border-slate-100
            bg-slate-50/70
            px-5
            py-4
          "
        >

          <div className="flex min-w-0 items-center gap-3">

            <button
              type="button"
              onClick={() =>
                toggleCategory(
                  category.id
                )
              }
              disabled={
                categoryTopics.length === 0
              }
              className="
                flex
                h-8
                w-8
                shrink-0
                items-center
                justify-center
                rounded-md
                text-slate-500
                hover:bg-white
                hover:text-slate-700
                disabled:cursor-default
                disabled:opacity-30
                disabled:hover:bg-transparent
              "
              aria-label={
                expanded
                  ? "Collapse category"
                  : "Expand category"
              }
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>


            <div
              className="
                flex
                h-10
                w-10
                shrink-0
                items-center
                justify-center
                rounded-lg
                bg-[#4A3FD6]
                text-white
              "
            >
              <FolderTree className="h-5 w-5" />
            </div>


            <div className="min-w-0">

              <div
                className="
                  flex
                  flex-wrap
                  items-center
                  gap-2
                "
              >

                <span
                  className="
                    text-sm
                    font-semibold
                    text-slate-900
                  "
                >
                  {category.code}
                </span>

                <span
                  className="
                    truncate
                    text-sm
                    font-semibold
                    text-slate-900
                  "
                >
                  {category.name}
                </span>

                {renderCategoryBadge(
                  category.code
                )}

              </div>

              <p className="mt-1 text-xs text-slate-500">
                {categoryTopics.length}{" "}
                {categoryTopics.length === 1
                  ? "topic"
                  : "topics"}
              </p>

            </div>

          </div>


          <div
            className="
              flex
              shrink-0
              items-center
              gap-2
            "
          >

            <Button
              size="sm"
              onClick={() =>
                handleAddTopic(
                  category
                )
              }
              className="
                bg-[#4A3FD6]
                hover:bg-[#4036C0]
              "
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Add Topic
            </Button>

          </div>

        </div>


        {/* ==================================================
            TOPICS (TREE)
        ================================================== */}

        {expanded && (

          <div className="p-5">

            {categoryTopics.length > 0 ? (

             <div className="relative ml-4 pl-8">
                {categoryTopics.map(
                  (topic, index) =>
                    renderTopic(
                      topic,
                      index === categoryTopics.length - 1
                    )
                )}
              </div>

            ) : (

              <div
                className="
                  rounded-lg
                  border
                  border-dashed
                  border-slate-200
                  bg-slate-50/50
                  px-5
                  py-8
                  text-center
                "
              >

                <p
                  className="
                    text-sm
                    font-medium
                    text-slate-600
                  "
                >
                  No topics in this category
                </p>

                <p
                  className="
                    mt-1
                    text-xs
                    text-slate-500
                  "
                >
                  Add a topic to start building
                  this section of the library.
                </p>

                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() =>
                    handleAddTopic(
                      category
                    )
                  }
                >
                  <Plus className="mr-1.5 h-4 w-4" />
                  Add Topic
                </Button>

              </div>

            )}

          </div>

        )}

      </div>
    );

  };


  /* ========================================================
     PAGE
  ======================================================== */

  return (

    <AppShell
      title="Topic Library"
      description="Browse and manage ESG materiality categories, topics, and sub-topics."
    >

      <div className="space-y-6">

        {/* ==================================================
            PAGE HEADER
        ================================================== */}

        {/* ==================================================
            TOOLBAR
        ================================================== */}

        <Card
          className="
            border-slate-200
            shadow-sm
          "
        >

          <CardContent className="p-4">

            <div
              className="
                flex
                flex-col
                gap-3
                md:flex-row
                md:items-center
              "
            >

              {/* SEARCH */}

              <div className="relative flex-1">

                <Search
                  className="
                    absolute
                    left-3
                    top-1/2
                    h-4
                    w-4
                    -translate-y-1/2
                    text-slate-400
                  "
                />

                <Input
                  value={search}
                  onChange={(event) =>
                    setSearch(
                      event.target.value
                    )
                  }
                  placeholder="Search categories, topics or sub-topics..."
                  className="
                    pl-9
                  "
                />

              </div>


              {/* STATUS */}

              <Select
                value={
                  statusFilter
                }
                onValueChange={(
                  value
                ) =>
                  setStatusFilter(
                    value as StatusFilter
                  )
                }
              >

                <SelectTrigger
                  className="w-full md:w-40"
                >
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>

                  <SelectItem value="All">
                    All Status
                  </SelectItem>

                  <SelectItem value="Active">
                    Active
                  </SelectItem>

                  <SelectItem value="Inactive">
                    Inactive
                  </SelectItem>

                </SelectContent>

              </Select>


              {/* EXPAND / COLLAPSE */}

              <div className="flex items-center gap-2">

                <Button
                  variant="outline"
                  onClick={expandAll}
                  disabled={
                    loading ||
                    filteredCategories.length === 0
                  }
                >
                  Expand All
                </Button>

                <Button
                  variant="outline"
                  onClick={collapseAll}
                  disabled={
                    loading ||
                    filteredCategories.length === 0
                  }
                >
                  Collapse All
                </Button>

              </div>


              {/* REFRESH */}

             <Button
            onClick={
              handleAddCategory
            }
            className="
              bg-[#4A3FD6]
              hover:bg-[#4036C0]
            "
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Category
          </Button>

            </div>

          </CardContent>

        </Card>


        {/* ==================================================
            TREE
        ================================================== */}

        <Card
          className="
            border-slate-200
            shadow-sm
          "
        >

          <CardHeader
            className="
              border-b
              border-slate-100
              px-5
              py-4
            "
          >

            <div
              className="
                flex
                items-center
                justify-between
                gap-3
              "
            >

              <div>

                <CardTitle
                  className="
                    text-base
                    font-semibold
                    text-slate-900
                  "
                >
                  ESG Topic Structure
                </CardTitle>

                <p
                  className="
                    mt-1
                    text-xs
                    text-slate-500
                  "
                >
                  Category → Topic → Sub-topic
                </p>

              </div>

              <Badge
                className="
                  border
                  border-slate-200
                  bg-slate-50
                  text-slate-600
                  hover:bg-slate-50
                "
              >
                {filteredCategories.length}{" "}
                categories
              </Badge>

            </div>

          </CardHeader>


          <CardContent className="p-5">

            {filteredCategories.length > 0 &&
              !loading &&
              !error && (

                <div className="space-y-4">

                  {filteredCategories.map(
                    renderCategory
                  )}

                </div>

              )}

            {renderEmptyState()}

          </CardContent>

        </Card>


        {/* ==================================================
            TOPIC LIBRARY DIALOG
        ================================================== */}

        <TopicLibraryDialog
          key={`${dialogMode}-${selectedCategory?.id ?? ""}-${selectedTopic?.id ?? ""}`}
          open={
            dialogMode !== null
          }
          mode={
            dialogMode
          }
          categories={
            categories
          }
          topics={
            topics
          }
          selectedCategory={
            selectedCategory
          }
          selectedTopic={
            selectedTopic
          }
          onClose={
            handleDialogClose
          }
          onSaved={
            loadLibrary
          }
        />

      </div>

    </AppShell>
  );
}