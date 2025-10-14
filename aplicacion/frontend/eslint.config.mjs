// eslint.config.mjs
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import eslintPluginReact from 'eslint-plugin-react';
import eslintPluginReactHooks from 'eslint-plugin-react-hooks';
import eslintPluginUnusedImports from 'eslint-plugin-unused-imports';
import eslintConfigPrettier from 'eslint-config-prettier';
import simpleImportSort from 'eslint-plugin-simple-import-sort';

export default [
  { ignores: ['.next/**', 'node_modules/**', 'dist/**', 'coverage/**', 'next-env.d.ts'] },

  {
    files: ['**/*.{js,mjs,cjs}'],
    ...js.configs.recommended,
  },

  // Reglas TypeScript
  ...tseslint.config({
    files: ['**/*.{ts,tsx}'],
    extends: [...tseslint.configs.recommended, eslintConfigPrettier],
    plugins: {
      'unused-imports': eslintPluginUnusedImports,
      'simple-import-sort': simpleImportSort,
    },
    rules: {
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'unused-imports/no-unused-imports': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { vars: 'all', args: 'after-used', ignoreRestSiblings: true },
      ],
      // ✅ Ordenación y limpieza de imports con ESLint
      'simple-import-sort/imports': 'warn',
      'simple-import-sort/exports': 'warn',
    },
    languageOptions: {
      parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    },
  }),

  // Reglas React (TS/JS/JSX/TSX)
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    plugins: { react: eslintPluginReact, 'react-hooks': eslintPluginReactHooks },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/jsx-uses-react': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
    settings: { react: { version: 'detect' } },
  },
];
