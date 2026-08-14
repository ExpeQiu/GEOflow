import { redirect } from "next/navigation";

export default function OperationsNewTaskRedirect() {
  redirect("/production/tasks/new");
}
