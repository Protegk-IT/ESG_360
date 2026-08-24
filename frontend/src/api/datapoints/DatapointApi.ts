import api from "@/services/api";

import type {
  Datapoint,
  DatapointDetail,
  DatapointFormData,
  DatapointCategory,
  DatapointCategoryFormData,
  UnitFamily,
  UnitFamilyFormData,
  Unit,
  UnitFormData,
  DatapointOption,
  DatapointOptionFormData,
  DatapointTableColumn,
  DatapointTableColumnFormData,
  DatapointTableRow,
  DatapointTableRowFormData,
  DatapointTableDefinition,
} from "@/types/datapoint";

/* ==========================================================
   BASE URL

   Django:
   /api/datapoints/
   ========================================================== */

const BASE_URL = "/datapoints";

const DatapointApi = {
  /* ========================================================
     DATAPOINTS
  ======================================================== */

  getAll() {
    return api.get<Datapoint[]>(`${BASE_URL}/`);
  },

  getById(id: string) {
    return api.get<DatapointDetail>(
      `${BASE_URL}/${id}/`
    );
  },

  create(data: DatapointFormData) {
    return api.post<Datapoint>(
      `${BASE_URL}/`,
      data
    );
  },

  update(
    id: string,
    data: DatapointFormData
  ) {
    return api.put<Datapoint>(
      `${BASE_URL}/${id}/`,
      data
    );
  },

  partialUpdate(
    id: string,
    data: Partial<DatapointFormData>
  ) {
    return api.patch<Datapoint>(
      `${BASE_URL}/${id}/`,
      data
    );
  },

  delete(id: string) {
    return api.delete(
      `${BASE_URL}/${id}/`
    );
  },

  /* ========================================================
     DATAPOINT OPTIONS
     GET    /api/datapoints/{id}/options/
     GET    /api/datapoints/options/
     POST   /api/datapoints/options/
     PUT    /api/datapoints/options/{id}/
     DELETE /api/datapoints/options/{id}/
  ======================================================== */

  getOptions(id: string) {
    return api.get<DatapointOption[]>(
      `${BASE_URL}/${id}/options/`
    );
  },

  /* ========================================================
     TABLE DEFINITION
     GET /api/datapoints/{id}/table-definition/
  ======================================================== */

  getTableDefinition(id: string) {
    return api.get<DatapointTableDefinition>(
      `${BASE_URL}/${id}/table-definition/`
    );
  },

  /* ========================================================
     CATEGORIES
     GET    /api/datapoints/categories/
     GET    /api/datapoints/categories/{id}/
     POST   /api/datapoints/categories/
     PUT    /api/datapoints/categories/{id}/
     DELETE /api/datapoints/categories/{id}/
  ======================================================== */

  getCategories() {
    return api.get<DatapointCategory[]>(
      `${BASE_URL}/categories/`
    );
  },

  getCategoryById(id: string) {
    return api.get<DatapointCategory>(
      `${BASE_URL}/categories/${id}/`
    );
  },

  createCategory(data: DatapointCategoryFormData) {
    return api.post<DatapointCategory>(
      `${BASE_URL}/categories/`,
      data
    );
  },

  updateCategory(
    id: string,
    data: DatapointCategoryFormData
  ) {
    return api.put<DatapointCategory>(
      `${BASE_URL}/categories/${id}/`,
      data
    );
  },

  deleteCategory(id: string) {
    return api.delete(
      `${BASE_URL}/categories/${id}/`
    );
  },

  /* ========================================================
     UNIT FAMILIES
     GET    /api/datapoints/unit-families/
     GET    /api/datapoints/unit-families/{id}/
     POST   /api/datapoints/unit-families/
     PUT    /api/datapoints/unit-families/{id}/
     DELETE /api/datapoints/unit-families/{id}/
  ======================================================== */

  getUnitFamilies() {
    return api.get<UnitFamily[]>(
      `${BASE_URL}/unit-families/`
    );
  },

  getUnitFamilyById(id: string) {
    return api.get<UnitFamily>(
      `${BASE_URL}/unit-families/${id}/`
    );
  },

  createUnitFamily(data: UnitFamilyFormData) {
    return api.post<UnitFamily>(
      `${BASE_URL}/unit-families/`,
      data
    );
  },

  updateUnitFamily(
    id: string,
    data: UnitFamilyFormData
  ) {
    return api.put<UnitFamily>(
      `${BASE_URL}/unit-families/${id}/`,
      data
    );
  },

  deleteUnitFamily(id: string) {
    return api.delete(
      `${BASE_URL}/unit-families/${id}/`
    );
  },

  /* ========================================================
     UNITS
     GET    /api/datapoints/units/
     GET    /api/datapoints/units/{id}/
     POST   /api/datapoints/units/
     PUT    /api/datapoints/units/{id}/
     DELETE /api/datapoints/units/{id}/
  ======================================================== */

  getUnits() {
    return api.get<Unit[]>(
      `${BASE_URL}/units/`
    );
  },

  getUnitsByFamily(familyId: string) {
    return api.get<Unit[]>(
      `${BASE_URL}/units/?family=${familyId}`
    );
  },

  getUnitById(id: string) {
    return api.get<Unit>(
      `${BASE_URL}/units/${id}/`
    );
  },

  createUnit(data: UnitFormData) {
    return api.post<Unit>(
      `${BASE_URL}/units/`,
      data
    );
  },

  updateUnit(id: string, data: UnitFormData) {
    return api.put<Unit>(
      `${BASE_URL}/units/${id}/`,
      data
    );
  },

  deleteUnit(id: string) {
    return api.delete(
      `${BASE_URL}/units/${id}/`
    );
  },

  /* ========================================================
     OPTIONS
     GET /api/datapoints/options/
  ======================================================== */

  getAllOptions() {
    return api.get<DatapointOption[]>(
      `${BASE_URL}/options/`
    );
  },

  createOption(data: DatapointOptionFormData) {
    return api.post<DatapointOption>(
      `${BASE_URL}/options/`,
      data
    );
  },

  updateOption(
    id: string,
    data: DatapointOptionFormData
  ) {
    return api.put<DatapointOption>(
      `${BASE_URL}/options/${id}/`,
      data
    );
  },

  deleteOption(id: string) {
    return api.delete(
      `${BASE_URL}/options/${id}/`
    );
  },

  /* ========================================================
     TABLE COLUMNS
     GET /api/datapoints/table-columns/
  ======================================================== */

  getTableColumns(datapointId?: string) {
    const params = datapointId
      ? { datapoint: datapointId }
      : undefined;

    return api.get<DatapointTableColumn[]>(
      `${BASE_URL}/table-columns/`,
      { params }
    );
  },

  createTableColumn(data: DatapointTableColumnFormData) {
    return api.post<DatapointTableColumn>(
      `${BASE_URL}/table-columns/`,
      data
    );
  },

  updateTableColumn(
    id: string,
    data: DatapointTableColumnFormData
  ) {
    return api.put<DatapointTableColumn>(
      `${BASE_URL}/table-columns/${id}/`,
      data
    );
  },

  deleteTableColumn(id: string) {
    return api.delete(
      `${BASE_URL}/table-columns/${id}/`
    );
  },

  /* ========================================================
     TABLE ROWS
     GET /api/datapoints/table-rows/
  ======================================================== */

  getTableRows(datapointId?: string) {
    const params = datapointId
      ? { datapoint: datapointId }
      : undefined;

    return api.get<DatapointTableRow[]>(
      `${BASE_URL}/table-rows/`,
      { params }
    );
  },

  createTableRow(data: DatapointTableRowFormData) {
    return api.post<DatapointTableRow>(
      `${BASE_URL}/table-rows/`,
      data
    );
  },

  updateTableRow(
    id: string,
    data: DatapointTableRowFormData
  ) {
    return api.put<DatapointTableRow>(
      `${BASE_URL}/table-rows/${id}/`,
      data
    );
  },

  deleteTableRow(id: string) {
    return api.delete(
      `${BASE_URL}/table-rows/${id}/`
    );
  },
};

export default DatapointApi;