
import Footer from "@/landing/Footer";
import Header from "@/landing/Header";
import Content from "@/landing/Content";
import Image from "next/image";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <Content />
      <Footer />
    </div>
  );
}
