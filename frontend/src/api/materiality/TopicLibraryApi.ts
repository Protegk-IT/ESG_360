import api from "@/services/api";

import type {
  TopicCategory,
  MaterialTopic,
  MaterialSubTopic,
  TopicCategoryFormData,
  MaterialTopicFormData,
  MaterialSubTopicFormData,
} from "@/types/materiality/materiality";


const TopicLibraryApi = {

  /* ==========================================================
     CATEGORIES
  ========================================================== */

  getCategories() {
    return api.get<TopicCategory[]>(
      "/materiality/topics/categories/"
    );
  },

  createCategory(
    data: TopicCategoryFormData
  ) {
    return api.post<TopicCategory>(
      "/materiality/topics/categories/",
      data
    );
  },


  /* ==========================================================
     TOPICS
  ========================================================== */

  getTopics(params?: {
    category?: string;
    search?: string;
    is_active?: boolean;
  }) {
    return api.get<MaterialTopic[]>(
      "/materiality/topics/",
      {
        params,
      }
    );
  },

  createTopic(
    data: MaterialTopicFormData
  ) {
    return api.post<MaterialTopic>(
      "/materiality/topics/",
      data
    );
  },


  /* ==========================================================
     SUB-TOPICS
  ========================================================== */

  getSubTopics(params?: {
    topic?: string;
    category?: string;
    search?: string;
    is_active?: boolean;
  }) {
    return api.get<MaterialSubTopic[]>(
      "/materiality/topics/subtopics/",
      {
        params,
      }
    );
  },

  createSubTopic(
    data: MaterialSubTopicFormData
  ) {
    return api.post<MaterialSubTopic>(
      "/materiality/topics/subtopics/",
      data
    );
  },
};

export default TopicLibraryApi;