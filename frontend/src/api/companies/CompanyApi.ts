import api from "@/services/api";

import type {
  Company,
  Country,
  State,
  City,
} from "@/types/company";

const CompanyApi = {
  // ==========================
  // Company Profile
  // ==========================

  getProfile() {
    return api.get<Company>("/company/profile/");
  },

  create(data: FormData) {
    return api.post(
      "/company/profile/",
      data,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
  },

  update(data: FormData) {
    return api.patch(
      "/company/profile/",
      data,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
  },

  // ==========================
  // Master Data
  // ==========================

  getCountries() {
    return api.get<Country[]>("/company/countries/");
  },

  getStates(countryId?: string) {
    return api.get<State[]>("/company/states/", {
      params: countryId
        ? { country: countryId }
        : {},
    });
  },

  getCities(stateId?: string) {
    return api.get<City[]>("/company/cities/", {
      params: stateId
        ? { state: stateId }
        : {},
    });
  },
};

export default CompanyApi;
