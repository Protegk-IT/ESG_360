import {
  useState,
} from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

import { toast } from "sonner";

import TopicLibraryApi from "@/api/materiality/TopicLibraryApi";

import type {
  TopicCategory,
  MaterialTopic,
} from "@/types/materiality/materiality";


/* ==========================================================
   DIALOG TYPES
========================================================== */

export type TopicLibraryDialogMode =
  | "category"
  | "topic"
  | "subtopic"
  | null;


/* ==========================================================
   PROPS
========================================================== */

interface TopicLibraryDialogProps {
  open: boolean;

  mode: TopicLibraryDialogMode;

  categories: TopicCategory[];

  topics: MaterialTopic[];

  selectedCategory?: TopicCategory | null;

  selectedTopic?: MaterialTopic | null;

  onClose: () => void;

  onSaved: () => void;
}


/* ==========================================================
   CATEGORY FORM
========================================================== */

interface CategoryForm {
  code: "E" | "S" | "G";
  name: string;
  display_order: string;
}


/* ==========================================================
   TOPIC FORM
========================================================== */

interface TopicForm {
  category: string;
  name: string;
  description: string;
  display_order: string;
  is_active: boolean;
}


/* ==========================================================
   SUB-TOPIC FORM
========================================================== */

interface SubTopicForm {
  topic: string;
  name: string;
  description: string;
  display_order: string;
  is_active: boolean;
}


/* ==========================================================
   EMPTY FORM STATES
========================================================== */

const emptyCategoryForm: CategoryForm = {
  code: "E",
  name: "",
  display_order: "0",
};


const emptyTopicForm: TopicForm = {
  category: "",
  name: "",
  description: "",
  display_order: "0",
  is_active: true,
};


const emptySubTopicForm: SubTopicForm = {
  topic: "",
  name: "",
  description: "",
  display_order: "0",
  is_active: true,
};


/* ==========================================================
   COMPONENT
========================================================== */

export default function TopicLibraryDialog({
  open,
  mode,
  categories,
  topics,
  selectedCategory,
  selectedTopic,
  onClose,
  onSaved,
}: TopicLibraryDialogProps) {

  /* ========================================================
     FORM STATE
  ======================================================== */

  const [categoryForm, setCategoryForm] =
    useState<CategoryForm>({
      ...emptyCategoryForm,
      ...(selectedCategory
        ? {
            code: selectedCategory.code,
            name: selectedCategory.name,
            display_order: String(
              selectedCategory.display_order
            ),
          }
        : {}),
    });


  const [topicForm, setTopicForm] =
    useState<TopicForm>({
      ...emptyTopicForm,
      ...(selectedCategory
        ? {
            category: selectedCategory.id,
          }
        : {}),
    });


  const [subTopicForm, setSubTopicForm] =
    useState<SubTopicForm>({
      ...emptySubTopicForm,
      ...(selectedTopic
        ? {
            topic: selectedTopic.id,
          }
        : {}),
    });


  const [saving, setSaving] =
    useState(false);


  /* ========================================================
     FORM UPDATE HELPERS
  ======================================================== */

  const updateCategory = (
    field: keyof CategoryForm,
    value: string
  ) => {
    setCategoryForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };


  const updateTopic = (
    field: keyof TopicForm,
    value: string | boolean
  ) => {
    setTopicForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };


  const updateSubTopic = (
    field: keyof SubTopicForm,
    value: string | boolean
  ) => {
    setSubTopicForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };


  /* ========================================================
     API ERROR MESSAGE
  ======================================================== */

  const getErrorMessage = (
    error: unknown
  ): string => {

    if (
      typeof error === "object" &&
      error !== null &&
      "response" in error
    ) {

      const response = (
        error as {
          response?: {
            data?: unknown;
          };
        }
      ).response;

      const data = response?.data;

      if (
        typeof data === "object" &&
        data !== null
      ) {

        const detail = (
          data as {
            detail?: unknown;
          }
        ).detail;

        if (
          typeof detail === "string" &&
          detail.trim()
        ) {
          return detail;
        }

        for (
          const value of Object.values(data)
        ) {

          if (typeof value === "string") {
            return value;
          }

          if (
            Array.isArray(value) &&
            typeof value[0] === "string"
          ) {
            return value[0];
          }
        }
      }
    }

    return "Unable to save. Please try again.";
  };


  /* ========================================================
     DIALOG TITLE
  ======================================================== */

  const title =
    mode === "category"
      ? "Add Category"
      : mode === "topic"
        ? "Add Topic"
        : "Add Sub-topic";


  const description =
    mode === "category"
      ? "Create an ESG materiality category for the topic library."
      : mode === "topic"
        ? "Create a materiality topic under an ESG category."
        : "Create a sub-topic under a materiality topic.";

          /* ========================================================
     SAVE
  ======================================================== */

  const handleSave = async () => {

    try {

      setSaving(true);


      /* ======================================================
         CATEGORY
      ====================================================== */

      if (mode === "category") {

        const name =
          categoryForm.name.trim();

        if (!name) {

          toast.error(
            "Category name is required."
          );

          return;
        }

        await TopicLibraryApi.createCategory({
          code: categoryForm.code,
          name,
          display_order:
            Number(
              categoryForm.display_order
            ),
        });

        toast.success(
          "Category created successfully."
        );

        onSaved();
        onClose();

        return;
      }


      /* ======================================================
         TOPIC
      ====================================================== */

      if (mode === "topic") {

        const name =
          topicForm.name.trim();

        if (!topicForm.category) {

          toast.error(
            "Please select a category."
          );

          return;
        }

        if (!name) {

          toast.error(
            "Topic name is required."
          );

          return;
        }

        await TopicLibraryApi.createTopic({

          category:
            topicForm.category,

          name,

          description:
            topicForm.description.trim(),

          display_order:
            Number(
              topicForm.display_order
            ),

          is_active:
            topicForm.is_active,

        });

        toast.success(
          "Topic created successfully."
        );

        onSaved();
        onClose();

        return;
      }


      /* ======================================================
         SUB-TOPIC
      ====================================================== */

      if (mode === "subtopic") {

        const name =
          subTopicForm.name.trim();

        if (!subTopicForm.topic) {

          toast.error(
            "Please select a topic."
          );

          return;
        }

        if (!name) {

          toast.error(
            "Sub-topic name is required."
          );

          return;
        }

        await TopicLibraryApi.createSubTopic({

          topic:
            subTopicForm.topic,

          name,

          description:
            subTopicForm.description.trim(),

          display_order:
            Number(
              subTopicForm.display_order
            ),

          is_active:
            subTopicForm.is_active,

        });

        toast.success(
          "Sub-topic created successfully."
        );

        onSaved();
        onClose();

        return;
      }

    } catch (error) {

      console.error(
        "Topic library save failed:",
        error
      );

      toast.error(
        getErrorMessage(error)
      );

    } finally {

      setSaving(false);

    }
  };


  /* ========================================================
     UI
  ======================================================== */

  return (

    <Dialog
      open={open}
      onOpenChange={(next) => {

        if (!next && !saving) {
          onClose();
        }

      }}
    >

      <DialogContent
        className="
          max-h-[85vh]
          overflow-y-auto
          bg-white
          p-6
          shadow-2xl
          sm:max-w-lg
        "
      >

        {/* ====================================================
            HEADER
        ==================================================== */}

        <DialogHeader
          className="space-y-1.5"
        >

          <DialogTitle
            className="
              text-lg
              font-semibold
              text-[#22243A]
            "
          >
            {title}
          </DialogTitle>

          <DialogDescription
            className="
              text-sm
              leading-5
              text-[#6B7280]
            "
          >
            {description}
          </DialogDescription>

        </DialogHeader>


        {/* ====================================================
            FORM CONTENT
        ==================================================== */}

        <div className="py-3">

          {/* ==================================================
              CATEGORY FORM
          ================================================== */}

          {mode === "category" && (

            <div className="space-y-5">

              {/* =================================================
                  CATEGORY CODE
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Category Code
                </Label>

                <Select
                  value={
                    categoryForm.code
                  }
                  onValueChange={(value) =>
                    updateCategory(
                      "code",
                      value
                    )
                  }
                >

                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>

                    <SelectItem value="E">
                      Environmental
                    </SelectItem>

                    <SelectItem value="S">
                      Social
                    </SelectItem>

                    <SelectItem value="G">
                      Governance
                    </SelectItem>

                  </SelectContent>

                </Select>

              </div>


              {/* =================================================
                  CATEGORY NAME
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Category Name
                </Label>

                <Input
                  value={
                    categoryForm.name
                  }
                  onChange={(event) =>
                    updateCategory(
                      "name",
                      event.target.value
                    )
                  }
                  placeholder="e.g. Environmental"
                />

              </div>


              {/* =================================================
                  DISPLAY ORDER
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Display Order
                </Label>

                <Input
                  type="number"
                  min="0"
                  value={
                    categoryForm.display_order
                  }
                  onChange={(event) =>
                    updateCategory(
                      "display_order",
                      event.target.value
                    )
                  }
                />

                <p className="text-xs text-[#6B7280]">
                  Controls the order in which the
                  category appears in the library.
                </p>

              </div>

            </div>

          )}


          {/* ==================================================
              TOPIC FORM
          ================================================== */}

          {mode === "topic" && (

            <div className="space-y-5">

              {/* =================================================
                  CATEGORY
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Category
                </Label>

                <Select
                  value={
                    topicForm.category
                  }
                  onValueChange={(value) =>
                    updateTopic(
                      "category",
                      value
                    )
                  }
                >

                  <SelectTrigger>
                    <SelectValue
                      placeholder="Select category"
                    />
                  </SelectTrigger>

                  <SelectContent>

                    {categories.map(
                      (category) => (

                        <SelectItem
                          key={category.id}
                          value={category.id}
                        >
                          {category.name}
                        </SelectItem>

                      )
                    )}

                  </SelectContent>

                </Select>

              </div>


              {/* =================================================
                  TOPIC NAME
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Topic Name
                </Label>

                <Input
                  value={
                    topicForm.name
                  }
                  onChange={(event) =>
                    updateTopic(
                      "name",
                      event.target.value
                    )
                  }
                  placeholder="e.g. Climate Change"
                />

              </div>


              {/* =================================================
                  DESCRIPTION
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Description
                </Label>

                <Textarea
                  value={
                    topicForm.description
                  }
                  onChange={(event) =>
                    updateTopic(
                      "description",
                      event.target.value
                    )
                  }
                  placeholder="Describe the materiality topic..."
                  rows={4}
                />

              </div>


              {/* =================================================
                  DISPLAY ORDER
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Display Order
                </Label>

                <Input
                  type="number"
                  min="0"
                  value={
                    topicForm.display_order
                  }
                  onChange={(event) =>
                    updateTopic(
                      "display_order",
                      event.target.value
                    )
                  }
                />

                <p className="text-xs text-[#6B7280]">
                  Controls the order in which this
                  topic appears within its category.
                </p>

              </div>


              {/* =================================================
                  ACTIVE
              ================================================= */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                  rounded-lg
                  border
                  border-[#E5E7EB]
                  bg-[#FAFAFC]
                  px-4
                  py-3
                "
              >

                <div className="space-y-0.5">

                  <Label>
                    Active
                  </Label>

                  <p className="text-xs text-[#6B7280]">
                    Active topics are available in
                    the materiality topic library.
                  </p>

                </div>

                <Checkbox
                  checked={
                    topicForm.is_active
                  }
                  onCheckedChange={(checked) =>
                    updateTopic(
                      "is_active",
                      checked === true
                    )
                  }
                />

              </div>

            </div>

          )}
                    {/* ==================================================
              SUB-TOPIC FORM
          ================================================== */}

          {mode === "subtopic" && (

            <div className="space-y-5">

              {/* =================================================
                  TOPIC
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Topic
                </Label>

                <Select
                  value={
                    subTopicForm.topic
                  }
                  onValueChange={(value) =>
                    updateSubTopic(
                      "topic",
                      value
                    )
                  }
                >

                  <SelectTrigger>
                    <SelectValue
                      placeholder="Select topic"
                    />
                  </SelectTrigger>

                  <SelectContent>

                    {topics.map(
                      (topic) => (

                        <SelectItem
                          key={topic.id}
                          value={topic.id}
                        >
                          {topic.code} - {topic.name}
                        </SelectItem>

                      )
                    )}

                  </SelectContent>

                </Select>

                <p className="text-xs text-[#6B7280]">
                  The sub-topic will be created
                  under the selected materiality topic.
                </p>

              </div>


              {/* =================================================
                  SUB-TOPIC NAME
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Sub-topic Name
                </Label>

                <Input
                  value={
                    subTopicForm.name
                  }
                  onChange={(event) =>
                    updateSubTopic(
                      "name",
                      event.target.value
                    )
                  }
                  placeholder="e.g. Scope 1 Emissions"
                />

              </div>


              {/* =================================================
                  DESCRIPTION
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Description
                </Label>

                <Textarea
                  value={
                    subTopicForm.description
                  }
                  onChange={(event) =>
                    updateSubTopic(
                      "description",
                      event.target.value
                    )
                  }
                  placeholder="Describe the materiality sub-topic..."
                  rows={4}
                />

              </div>


              {/* =================================================
                  DISPLAY ORDER
              ================================================= */}

              <div className="space-y-1.5">

                <Label>
                  Display Order
                </Label>

                <Input
                  type="number"
                  min="0"
                  value={
                    subTopicForm.display_order
                  }
                  onChange={(event) =>
                    updateSubTopic(
                      "display_order",
                      event.target.value
                    )
                  }
                />

                <p className="text-xs text-[#6B7280]">
                  Controls the order of this
                  sub-topic within its topic.
                </p>

              </div>


              {/* =================================================
                  ACTIVE
              ================================================= */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                  rounded-lg
                  border
                  border-[#E5E7EB]
                  bg-[#FAFAFC]
                  px-4
                  py-3
                "
              >

                <div className="space-y-0.5">

                  <Label>
                    Active
                  </Label>

                  <p className="text-xs text-[#6B7280]">
                    Active sub-topics are available
                    for materiality assessments.
                  </p>

                </div>

                <Checkbox
                  checked={
                    subTopicForm.is_active
                  }
                  onCheckedChange={(checked) =>
                    updateSubTopic(
                      "is_active",
                      checked === true
                    )
                  }
                />

              </div>

            </div>

          )}

        </div>


        {/* ====================================================
            FOOTER
        ==================================================== */}

        <DialogFooter
          className="
            mt-2
            border-t
            border-[#E5E7EB]
            bg-white
            px-0
            pt-5
          "
        >

          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </Button>

          <Button
            type="button"
            onClick={handleSave}
            disabled={
              saving || !mode
            }
            className="
              bg-[#4A3FD6]
              hover:bg-[#4036C0]
            "
          >
            {saving
              ? "Saving..."
              : "Save"}
          </Button>

        </DialogFooter>

      </DialogContent>

    </Dialog>
  );
}