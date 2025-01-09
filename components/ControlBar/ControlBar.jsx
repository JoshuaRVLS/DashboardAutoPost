"use client";
import "./ControlBar.css";
import { AiFillPlayCircle } from "react-icons/ai";

import React, { useContext } from "react";
import { useSession } from "next-auth/react";
import AccountContext from "@/context/AccountContext";

const ControlBar = () => {
  const { data: session } = useSession();
  const { currentAccount } = useContext(AccountContext);

  return (
    <div className="control-bar">
      <AiFillPlayCircle className="icon" />
      <span className="bg-btnBackground shadow-xl p-2 rounded-md text-white">
        Bot is{" "}
        <span
          className={session?.user?.accounts[currentAccount]?.status === ""}
        ></span>
      </span>
    </div>
  );
};

export default ControlBar;
