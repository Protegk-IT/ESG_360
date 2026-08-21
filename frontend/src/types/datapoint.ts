/* ==========================================================
   DATAPOINT TYPES
   ----------------------------------------------------------
   Frontend contract matching the current M4 Django models
   and serializers.

   Backend source of truth:
   - Datapoint
   - DatapointCategory
   - DatapointOption
   - DatapointTableColumn
   - DatapointTableRow
   - UnitFamily
   - Unit

   IMPORTANT:
   These types match the serializers currently implemented.
   ========================================================== */


/* ==========================================================
   DATA TYPE
========================================================== */

export type DatapointDataType =
  | "DECIMAL"
  | "INTEGER"
  | "TEXT"
  | "LONG_TEXT"
  | "BOOLEAN"
  | "SELECT"
  | "DATE"
  | "TABLE";

export type ValidationMetadata = Record<string, unknown>;


/* ==========================================================
   COLLECTION LEVEL
========================================================== */

export type CollectionLevel =
  | "COMPANY"
  | "ORG_NODE"
  | "FACILITY"
  | "ANY";


/* ==========================================================
   COLLECTION FREQUENCY
========================================================== */

export type CollectionFrequency =
  | "MONTHLY"
  | "QUARTERLY"
  | "ANNUAL";


/* ==========================================================
   ESG PILLAR
========================================================== */

export type ESGPillar =
  | "E"
  | "S"
  | "G";


/* ==========================================================
   UNIT FAMILY
   ----------------------------------------------------------
   Backend:
       class UnitFamily(BaseModel)
========================================================== */

export interface UnitFamily {
  id: string;

  code: string;
  name: string;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   UNIT
   ----------------------------------------------------------
   Backend:
       class Unit(BaseModel)
========================================================== */

export interface Unit {
  id: string;

  /*
   * ForeignKey -> UnitFamily
   */
  family: string;

  code: string;
  name: string;

  factor_to_base: string;

  is_base_unit: boolean;
  is_active: boolean;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   UNIT DETAILS
   ----------------------------------------------------------
   Optional frontend representation when the related family
   is explicitly included by a future/nested serializer.

   Current UnitSerializer does NOT return family_details.
========================================================== */

export interface UnitDetails extends Unit {
  family_details?: UnitFamily;
}


/* ==========================================================
   DATAPOINT CATEGORY
   ----------------------------------------------------------
   Backend:
       class DatapointCategory(BaseModel)

   Current serializer fields:
       id
       code
       name
       description
       module
       esg_pillar
       display_order
       is_active
       created_at
       updated_at
========================================================== */

export interface DatapointCategory {
  id: string;

  code: string;
  name: string;
  description: string;

  /*
   * ForeignKey -> modules.Module
   *
   * Backend uses:
   *   to_field="code"
   *   db_column="module_code"
   *
   * DRF serializer returns the related value.
   */
  module: string;

  esg_pillar: ESGPillar | null;

  display_order: number;
  is_active: boolean;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   DATAPOINT OPTION
   ----------------------------------------------------------
   Backend:
       class DatapointOption(BaseModel)

   Only valid for SELECT datapoints.
========================================================== */

export interface DatapointOption {
  id: string;

  /*
   * ForeignKey -> Datapoint
   */
  datapoint: string;

  code: string;
  label: string;

  display_order: number;
  is_active: boolean;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   DATAPOINT TABLE COLUMN
   ----------------------------------------------------------
   Backend:
       class DatapointTableColumn(BaseModel)

   Only valid for TABLE datapoints.
========================================================== */

export interface DatapointTableColumn {
  id: string;

  /*
   * ForeignKey -> Datapoint
   */
  datapoint: string;

  code: string;
  label: string;

  data_type: DatapointDataType;

  /*
   * ForeignKey -> UnitFamily
   */
  unit_family: string | null;

  /*
   * ForeignKey -> Unit
   */
  default_unit: string | null;

  is_required: boolean;
  validation_metadata: ValidationMetadata;

  display_order: number;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   DATAPOINT TABLE ROW
   ----------------------------------------------------------
   Backend:
       class DatapointTableRow(BaseModel)

   Only valid for TABLE datapoints.
========================================================== */

export interface DatapointTableRow {
  id: string;

  /*
   * ForeignKey -> Datapoint
   */
  datapoint: string;

  code: string;
  label: string;

  display_order: number;

  created_at: string;
  updated_at: string;
}


/* ==========================================================
   DATAPOINT
   ----------------------------------------------------------
   Backend:
       class Datapoint(BaseModel)

   Current DatapointSerializer fields:
       id
       code
       category
       module
       label
       description
       data_type
       unit_family
       default_unit
       collection_level
       frequency
       is_required
       display_order
       is_active
       created_at
       updated_at
========================================================== */

export interface Datapoint {
  id: string;

  code: string;

  category: string;

  module: string;

  label: string;

  description: string;

  data_type: DatapointDataType;

  unit_family: string | UnitFamily | null;

  default_unit: string | Unit | null;

  collection_level: CollectionLevel;

  frequency: CollectionFrequency;

  is_required: boolean;

  allow_dynamic_rows: boolean;

  validation_metadata: ValidationMetadata;

  display_order: number;

  is_active: boolean;

  created_at: string;

  updated_at: string;
}

/* ==========================================================
   DATAPOINT DETAIL
   ----------------------------------------------------------
   The standard DatapointSerializer does NOT return nested
   relationships.

   These optional properties are populated by the frontend
   when calling:

       GET /datapoints/:id/options/

   or:

       GET /datapoints/:id/table-definition/
========================================================== */

export interface DatapointDetail extends Datapoint {
  /*
   * Optional category information if available.
   */
  category_details?: DatapointCategory;

  /*
   * Optional unit family information if available.
   */
  unit_family_details?: UnitFamily;

  /*
   * Optional default unit information if available.
   */
  default_unit_details?: Unit;

  /*
   * SELECT datapoint
   */
  options?: DatapointOption[];

  /*
   * TABLE datapoint
   */
  table_columns?: DatapointTableColumn[];

  /*
   * TABLE datapoint
   */
  table_rows?: DatapointTableRow[];
}


/* ==========================================================
   TABLE DEFINITION RESPONSE
   ----------------------------------------------------------
   Backend endpoint:

       GET /datapoints/:id/table-definition/

   Current backend response:

   {
       datapoint: Datapoint,
       columns: [...],
       rows: [...]
   }
========================================================== */

export interface DatapointTableDefinition {
  datapoint: Datapoint;

  columns: DatapointTableColumn[];

  rows: DatapointTableRow[];
}


/* ==========================================================
   DATAPOINT FILTERS
   ----------------------------------------------------------
   Matches DatapointViewSet.filterset_fields and
   SearchFilter.
========================================================== */

export interface DatapointFilters {
  search?: string;

  module?: string;

  category?: string;

  data_type?: DatapointDataType;

  is_active?: boolean;

  collection_level?: CollectionLevel;

  frequency?: CollectionFrequency;

  is_required?: boolean;

  ordering?: string;
}


/* ==========================================================
   DATAPOINT FORM DATA
   ----------------------------------------------------------
   Used when creating/updating a Datapoint.

   ForeignKey fields are sent as IDs/related values.
========================================================== */

export interface DatapointFormData {
  code: string;

  category: string;

  module: string;

  label: string;

  description: string;

  data_type: DatapointDataType;

  unit_family?: string | null;

  default_unit?: string | null;

  collection_level: CollectionLevel;

  frequency: CollectionFrequency;

  is_required: boolean;

  allow_dynamic_rows: boolean; 

  validation_metadata: ValidationMetadata;

  display_order: number;

  is_active: boolean;
}


/* ==========================================================
   DATAPOINT OPTION FORM DATA
========================================================== */

export interface DatapointOptionFormData {
  datapoint: string;

  code: string;

  label: string;

  display_order: number;

  is_active: boolean;
}


/* ==========================================================
   DATAPOINT TABLE COLUMN FORM DATA
========================================================== */

export interface DatapointTableColumnFormData {
  datapoint: string;

  code: string;

  label: string;

  data_type: DatapointDataType;

  unit_family?: string | null;

  default_unit?: string | null;

  validation_metadata: ValidationMetadata;

  is_required: boolean;

  display_order: number;
}


/* ==========================================================
   DATAPOINT TABLE ROW FORM DATA
========================================================== */

export interface DatapointTableRowFormData {
  datapoint: string;

  code: string;

  label: string;

  display_order: number;
}


/* ==========================================================
   UNIT FAMILY FORM DATA
========================================================== */

export interface UnitFamilyFormData {
  code: string;

  name: string;
}


/* ==========================================================
   UNIT FORM DATA
========================================================== */

export interface UnitFormData {
  family: string;

  code: string;

  name: string;

  factor_to_base: string;

  is_base_unit: boolean;

  is_active: boolean;
}


/* ==========================================================
   CATEGORY FORM DATA
========================================================== */

export interface DatapointCategoryFormData {
  code: string;

  name: string;

  description: string;

  module: string;

  esg_pillar?: ESGPillar | null;

  display_order: number;

  is_active: boolean;
}

// Moduel

export interface Module {
  id: string;
  code: string;
  name: string;
  description: string;
  esg_pillar: ESGPillar | null;
  icon: string | null;
  is_core: boolean;
  is_enabled: boolean;
  display_order: number;
}