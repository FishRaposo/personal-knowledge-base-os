import NoteView from "@/components/NoteView";

export default function NotePage({ params }: { params: { id: string } }) {
  return <NoteView id={params.id} />;
}
