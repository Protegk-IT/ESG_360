/* ==========================================================
   TOPIC CATEGORY
========================================================== */

export interface TopicCategory {
  id: string;
  code: "E" | "S" | "G";
  name: string;
  display_order: number;
}


/* ==========================================================
   MATERIAL TOPIC
========================================================== */

export interface MaterialTopic {
  id: string;

  category: string;
  category_name: string;

  company: string | null;

  code: number;

  name: string;
  description: string;

  display_order: number;

  is_active: boolean;
}


/* ==========================================================
   MATERIAL SUB-TOPIC
========================================================== */

export interface MaterialSubTopic {
  id: string;

  topic: string;
  topic_name: string;

  topic_code: number;

  category_name: string;

  code: string;

  name: string;
  description: string;

  display_order: number;

  is_active: boolean;
}


/* ==========================================================
   CATEGORY FORM
========================================================== */

export interface TopicCategoryFormData {
  code: "E" | "S" | "G";
  name: string;
  display_order: number;
}


/* ==========================================================
   TOPIC FORM
========================================================== */

export interface MaterialTopicFormData {
  category: string;
  company?: string | null;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
}


/* ==========================================================
   SUB-TOPIC FORM
========================================================== */

export interface MaterialSubTopicFormData {
  topic: string;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
}