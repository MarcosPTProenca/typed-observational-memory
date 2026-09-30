# 项目自定义规则

## 项目概述

本项目是一个基于 uni-app 开发的跨平台手机壁纸应用，支持 H5、微信小程序和 App 三端。

## 技术栈

- 框架：uni-app（Vue 3 + Composition API）
- 状态管理：Pinia
- 网络请求：uni.request 封装
- 样式：SCSS，采用 BEM 命名规范

## 代码规范

- 组件文件名使用 PascalCase，如 `GoodsList.vue`
- 页面文件放在 `pages/` 目录，按模块分子目录
- 公共组件放在 `components/` 目录
- 工具函数放在 `utils/` 目录，按功能模块拆分
- 接口请求统一封装在 `api/` 目录

## 接口约定

- 后端接口基础地址通过 `BASE_URL` 环境变量配置
- 所有接口返回格式为 `{ code, data, message }`，code 为 200 表示成功
- Token 存储在 `uni.getStorageSync('token')` 中，请求头携带 `Authorization: Bearer <token>`

## 注意事项

- 不要使用 `window`、`document` 等浏览器专有 API，请使用 uni 提供的跨平台 API
- 图片资源统一放在 `static/` 目录，不要使用网络图片作为默认资源
- 涉及支付、授权等敏感功能，修改前请先查阅 `docs/` 目录下的相关说明文档