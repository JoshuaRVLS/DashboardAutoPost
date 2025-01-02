"use client";

import React, { useState } from "react";
import "./Navbar.css";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { motion } from "motion/react";
import { usePathname } from "next/navigation";

const Navbar = () => {
  const { data: session } = useSession();
  const path = usePathname();

  const [profileMenu, setProfileMenu] = useState(false);

  return (
    <motion.nav
      className={`navbar absolute`}
      animate={{ height: profileMenu ? "4rem" : "100dvh" }}
    >
      <div className="flex gap-4 items-center justify-center">
        <img
          onClick={() => setProfileMenu(!profileMenu)}
          className="photo"
          src={session?.user?.photo_profile}
        />
        <motion.span>{session?.user?.username}</motion.span>
      </div>
      <div className={`links ${session?.user?.expired ? "dead" : ""}`}>
        <Link className={path === "/dashboard" ? "link-active" : ""} href={"/"}>
          Status
        </Link>
      </div>
    </motion.nav>
  );
};

export default Navbar;
