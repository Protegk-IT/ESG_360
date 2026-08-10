import * as React from "react";

import { cn } from "@/lib/utils";

function Card({
  className,
  size = "default",
  ...props
}: React.ComponentProps<"div"> & {
  size?: "default" | "sm";
}) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        `
        group/card
        flex
        flex-col
        overflow-hidden

        rounded-xl

        border
        border-[#D9DEE8]

        bg-white

        shadow-sm

        transition-all
        duration-200

        hover:shadow-md

        [--card-spacing:24px]

        data-[size=sm]:[--card-spacing:16px]
        `,
        className
      )}
      {...props}
    />
  );
}

function CardHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        `
        flex
        flex-col
        gap-1

        border-b

        border-[#ECEEF5]

        bg-white

        px-[--card-spacing]
        py-5
        `,
        className
      )}
      {...props}
    />
  );
}

function CardTitle({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn(
        `
        text-lg
        font-semibold
        tracking-tight
        text-[#111827]
        `,
        className
      )}
      {...props}
    />
  );
}

function CardDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn(
        `
        mt-1
        text-sm
        leading-6
        text-[#6B7280]
        `,
        className
      )}
      {...props}
    />
  );
}

function CardAction({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        `
        ml-auto
        flex
        items-center
        gap-2
        `,
        className
      )}
      {...props}
    />
  );
}

function CardContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn(
        `
        flex-1

        px-[--card-spacing]

        py-6
        `,
        className
      )}
      {...props}
    />
  );
}

function CardFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        `
        flex
        items-center
        justify-between

        border-t

        border-[#ECEEF5]

        bg-[#FAFAFC]

        px-[--card-spacing]

        py-4
        `,
        className
      )}
      {...props}
    />
  );
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
};