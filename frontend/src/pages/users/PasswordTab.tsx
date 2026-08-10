import { useMemo, useState } from "react";

import {
  CheckCircle2,
  Eye,
  EyeOff,
  Key,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import type { UserFormData } from "@/types/user";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";

import { Input } from "@/components/ui/input";

import { Label } from "@/components/ui/label";

import { Progress } from "@/components/ui/progress";

interface Props {
  formData: UserFormData;

  updateField: <
    K extends keyof UserFormData
  >(
    field: K,
    value: UserFormData[K]
  ) => void;

  errors: Record<
    string,
    string[]
  >;
}

export default function PasswordTab({
  formData,
  updateField,
  errors,
}: Props) {

  /* ==========================================================
      STATE
  ========================================================== */

  const [
    showPassword,
    setShowPassword,
  ] = useState(false);

  const [
    showConfirm,
    setShowConfirm,
  ] = useState(false);

  /* ==========================================================
      PASSWORD STRENGTH
  ========================================================== */

  const checks = useMemo(() => {
    const password =
      formData.password;

    return {
      length:
        password.length >= 8,

      lowercase:
        /[a-z]/.test(password),

      uppercase:
        /[A-Z]/.test(password),

      number:
        /\d/.test(password),
    };
  }, [formData.password]);

  const strength =
    Object.values(checks).filter(
      Boolean
    ).length;

  const passwordMatch =
    formData.confirm_password.length ===
    0
      ? true
      : formData.password ===
        formData.confirm_password;

  const strengthLabel = [
    "Very Weak",
    "Weak",
    "Fair",
    "Good",
    "Strong",
  ][strength];

  const progressValue =
    strength * 25;

  const progressClass =
    strength <= 1
      ? "[&>div]:bg-red-500"
      : strength === 2
      ? "[&>div]:bg-yellow-500"
      : strength === 3
      ? "[&>div]:bg-blue-500"
      : "[&>div]:bg-green-600";

  /* ==========================================================
      REQUIREMENT ROW
  ========================================================== */

  const renderCheck = (
    valid: boolean,
    text: string
  ) => (
    <div className="flex items-center gap-3">

      {valid ? (

        <CheckCircle2
          className="
            h-5
            w-5
            text-green-600
          "
        />

      ) : (

        <XCircle
          className="
            h-5
            w-5
            text-red-500
          "
        />

      )}

      <span
        className={
          valid
            ? "text-green-700"
            : "text-muted-foreground"
        }
      >
        {text}
      </span>

    </div>
  );

  /* ==========================================================
      UI
  ========================================================== */

  return (
    <div className="space-y-8">
        {/* ======================================================
          PASSWORD INFORMATION
      ====================================================== */}

      <Card>

        <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">

          <CardTitle className="flex items-center gap-3">

            <div
              className="
                flex
                h-11
                w-11
                items-center
                justify-center
                rounded-xl
                bg-[#EEF2FF]
              "
            >
              <ShieldCheck
                className="
                  h-5
                  w-5
                  text-[#4A3FD6]
                "
              />
            </div>

            <div>

              <h2
                className="
                  text-lg
                  font-semibold
                  text-[#22243A]
                "
              >
                Password Information
              </h2>

              <CardDescription>
                Set a secure password for the user account.
              </CardDescription>

            </div>

          </CardTitle>

        </CardHeader>

        <CardContent className="space-y-8 p-8">

          {/* ======================================
              PASSWORD
          ====================================== */}

          <div className="space-y-2">

            <Label>
              Password
            </Label>

            <div className="relative">

              <Key
                className="
                  absolute
                  left-3
                  top-1/2
                  h-4
                  w-4
                  -translate-y-1/2
                  text-muted-foreground
                "
              />

              <Input
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                placeholder="Enter password"
                value={formData.password}
                onChange={(e) =>
                  updateField(
                    "password",
                    e.target.value
                  )
                }
                className="pl-10 pr-12"
              />

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="
                  absolute
                  right-1
                  top-1/2
                  h-8
                  w-8
                  -translate-y-1/2
                "
                onClick={() =>
                  setShowPassword(
                    !showPassword
                  )
                }
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>

            </div>

            {errors.password && (

              <p className="text-sm text-red-500">
                {errors.password[0]}
              </p>

            )}

          </div>

          {/* ======================================
              PASSWORD STRENGTH
          ====================================== */}

          <div className="space-y-3">

            <div className="flex items-center justify-between">

              <Label>
                Password Strength
              </Label>

              <span
                className="
                  text-sm
                  font-medium
                  text-[#4A3FD6]
                "
              >
                {strengthLabel}
              </span>

            </div>

            <Progress
              value={progressValue}
              className={progressClass}
            />

          </div>

          {/* ======================================
              CONFIRM PASSWORD
          ====================================== */}

          <div className="space-y-2">

            <Label>
              Confirm Password
            </Label>

            <div className="relative">

              <Key
                className="
                  absolute
                  left-3
                  top-1/2
                  h-4
                  w-4
                  -translate-y-1/2
                  text-muted-foreground
                "
              />

              <Input
                type={
                  showConfirm
                    ? "text"
                    : "password"
                }
                placeholder="Confirm password"
                value={
                  formData.confirm_password
                }
                onChange={(e) =>
                  updateField(
                    "confirm_password",
                    e.target.value
                  )
                }
                className="pl-10 pr-12"
              />

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="
                  absolute
                  right-1
                  top-1/2
                  h-8
                  w-8
                  -translate-y-1/2
                "
                onClick={() =>
                  setShowConfirm(
                    !showConfirm
                  )
                }
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>

            </div>

            {!passwordMatch && (

              <p className="text-sm text-red-500">
                Passwords do not match.
              </p>

            )}

            {errors.confirm_password && (

              <p className="text-sm text-red-500">
                {errors.confirm_password[0]}
              </p>

            )}

          </div>

        </CardContent>

      </Card> 
            {/* ======================================================
          PASSWORD REQUIREMENTS
      ====================================================== */}

      <Card>

        <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">

          <CardTitle className="text-lg font-semibold">
            Password Requirements
          </CardTitle>

          <CardDescription>
            The password should satisfy the following security requirements.
          </CardDescription>

        </CardHeader>

        <CardContent className="space-y-4 p-8">

          {renderCheck(
            checks.length,
            "Minimum 8 characters"
          )}

          {renderCheck(
            checks.lowercase,
            "At least one lowercase letter"
          )}

          {renderCheck(
            checks.uppercase,
            "At least one uppercase letter"
          )}

          {renderCheck(
            checks.number,
            "At least one number"
          )}

        </CardContent>

      </Card>

      {/* ======================================================
          PASSWORD POLICY
      ====================================================== */}

      <Card>

        <CardHeader className="border-b bg-[#F8F9FC] px-8 py-6">

          <CardTitle className="text-lg font-semibold">
            Password Policy
          </CardTitle>

          <CardDescription>
            Follow these recommendations to improve account security.
          </CardDescription>

        </CardHeader>

        <CardContent className="p-8">

          <ul className="list-disc space-y-3 pl-5 text-sm text-[#4B5563]">

            <li>
              Use at least <strong>8 characters</strong>.
            </li>

            <li>
              Include uppercase and lowercase letters.
            </li>

            <li>
              Include at least one numeric character.
            </li>

            <li>
              Avoid using personal information such as names or birthdays.
            </li>

            <li>
              Avoid common or easily guessed passwords.
            </li>

            <li>
              Use a unique password for every account whenever possible.
            </li>

          </ul>

        </CardContent>

      </Card>

    </div>
  );
}