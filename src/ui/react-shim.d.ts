// Minimal React/JSX type shims for this repo.
// This project’s UI bundle may be built elsewhere; these shims keep TS tooling quiet
// in environments where node_modules/@types/react is not installed.

declare module "react" {
  export type ReactNode = any;
  export type FC<P = {}> = (props: P) => any;
  export const Fragment: any;
  const React: any;
  export default React;
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

// LangGraph React UI SDK (generative UI)
// 在本仓库里我们不强依赖 node_modules 的类型声明，因此用 any 兜底。
declare module "@langchain/langgraph-sdk/react-ui" {
  export function useStreamContext<TProps = any, TMeta = any>(): any;
}

declare global {
  namespace JSX {
    interface ElementChildrenAttribute {
      children: {};
    }
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
