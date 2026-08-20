import * as React from "react";
import {
  Controller,
  FormProvider,
  useFormContext,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
} from "react-hook-form";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

/* ==========================================================
   FORM
========================================================== */

const Form = FormProvider;

/* ==========================================================
   FORM FIELD
========================================================== */

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> = {
  name: TName;
};

const FormFieldContext =
  React.createContext<FormFieldContextValue | null>(null);

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
  ...props
}: ControllerProps<TFieldValues, TName>) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  );
};

/* ==========================================================
   FORM ITEM
========================================================== */

type FormItemContextValue = {
  id: string;
};

const FormItemContext =
  React.createContext<FormItemContextValue | null>(null);

function FormItem({ className, ...props }: React.ComponentProps<"div">) {
  const id = React.useId();

  return (
    <FormItemContext.Provider value={{ id }}>
      <div
        data-slot="form-item"
        className={cn("grid gap-2", className)}
        {...props}
      />
    </FormItemContext.Provider>
  );
}

/* ==========================================================
   FIELD STATE
========================================================== */

function useFormField() {
  const fieldContext = React.useContext(FormFieldContext);
  const itemContext = React.useContext(FormItemContext);
  const { getFieldState } = useFormContext();

  if (!fieldContext || !itemContext) {
    throw new Error(
      "useFormField must be used inside FormField and FormItem"
    );
  }

  const fieldState = getFieldState(fieldContext.name);
  const id = itemContext.id;

  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  };
}

/* ==========================================================
   FORM LABEL
========================================================== */

function FormLabel({
  className,
  ...props
}: React.ComponentProps<typeof Label>) {
  const { error, formItemId } = useFormField();

  return (
    <Label
      data-slot="form-label"
      data-error={!!error}
      htmlFor={formItemId}
      className={cn(
        "text-sm font-medium text-foreground",
        "data-[error=true]:text-red-600",
        className
      )}
      {...props}
    />
  );
}

/* ==========================================================
   FORM CONTROL
========================================================== */

function FormControl({ ...props }: React.ComponentProps<typeof Slot>) {
  const { error, formItemId, formDescriptionId, formMessageId } =
    useFormField();

  const describedBy = error
    ? `${formDescriptionId} ${formMessageId}`
    : formDescriptionId;

  return (
    <Slot
      data-slot="form-control"
      id={formItemId}
      aria-describedby={describedBy}
      aria-invalid={!!error}
      {...props}
    />
  );
}

/* ==========================================================
   FORM DESCRIPTION
========================================================== */

function FormDescription({ className, ...props }: React.ComponentProps<"p">) {
  const { formDescriptionId } = useFormField();

  return (
    <p
      data-slot="form-description"
      id={formDescriptionId}
      className={cn("text-sm leading-relaxed text-muted-foreground", className)}
      {...props}
    />
  );
}

/* ==========================================================
   FORM MESSAGE
========================================================== */

function FormMessage({
  className,
  children,
  ...props
}: React.ComponentProps<"p">) {
  const { error, formMessageId } = useFormField();

  const body = error?.message ? String(error.message) : children;

  if (!body) {
    return null;
  }

  return (
    <p
      data-slot="form-message"
      id={formMessageId}
      className={cn("text-sm font-medium text-red-600", className)}
      {...props}
    >
      {body}
    </p>
  );
}

/* ==========================================================
   EXPORTS
========================================================== */

export {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  useFormField,
};